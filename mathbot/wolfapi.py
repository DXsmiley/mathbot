import aiohttp
import xmltodict
import json
import asyncio
import PIL
import PIL.Image
import io
import typing


italify = '*{}*'.format
boldify = '**{}**'.format
codify = '`{}`'.format


# ASSUMPTION_EMOJI = '🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿'
ASSUMPTION_EMOJI = '🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿'
UNKNOWN_EMOJI = '❔'

# There's a thing called 'podstates' which may be required to show
# additional information. The API documentation doesn't have a list
# of all the pod states, so I'm logging them and putting them here
# as I discover them (or adding them to WOLF_PODSTATES if it's useful
# to include them in queries)
UNINTERESTING_PODSTATES = [
	'Result__Step-by-step solution',
	'DecimalApproximation__Fewer digits',
	'Result__Hide limits'
]

WOLF_PODSTATES = [
	'Result__Show limits',
	'DecimalApproximation__More digits'
]


ALL_PODSTATES = UNINTERESTING_PODSTATES + WOLF_PODSTATES


class WolframError(Exception):

	def __init__(self, text: str) -> None:
		self.text = text

	def __str__(self) -> str:
		return 'W|A Error: ' + self.text


class WolframDidntSucceed(Exception):

	def __init__(self, tips: typing.List[str]) -> None:
		self.tips = tips

	def __str__(self) -> str:
		return 'W|A Didn\'t succeed'


class NoImageError(Exception):

	def __str__(self) -> str:
		return "Images for this request have not been downloaded yet and cannot be accessed."


class Result:

	def __init__(self, qr):

		if qr['@error'] == 'true':
			raise WolframError(qr['error'].get('@msg', ''))

		if qr['@success'] == 'false':
			raise WolframDidntSucceed([
				tip['@text']
				for tip in listify(qr['tips']['tip'])
			] if 'tips' in qr else [])

		self.sections = [
			Section(pod)
			for pod in listify(qr.get('pod', []))
		]

		self.assumptions = Assumptions(
			listify(qr['assumptions']['assumption'])
			if 'assumptions' in qr else []
		)

		self.timeouts = list(filter(bool, qr.get('@timedout', '').split(',')))

	def __repr__(self):
		return f'Result(sections={self.sections}, assumptions={self.assumptions}, timeouts={self.timeouts})'

	async def download_images(self, session):
		futures = [i.get_futures(session) for i in self.sections]
		await asyncio.gather(*futures)


class Client:

	def __init__(self, appid, server = None):
		self._appid = appid
		self._server = server or 'https://api.wolframalpha.com/v2/query'
		self._default_width = None
		self._default_max_width = None
		self._default_plot_with = None
		self._default_location = None

	async def request(self, query: str, assumptions: typing.List[str] = [], *, session=None, **kwargs) -> Result:
		if session is None:
			async with aiohttp.ClientSession() as session:
				return await self._request(query, assumptions, session=session, **kwargs)
		else:
			return await self._request(query, assumptions, session=session, **kwargs)	

	async def _request(self, query: str, assumptions: typing.List[str] = [], *, session: aiohttp.ClientSession, imperial: bool=False, debug: bool=False, download_images: bool=True, timeout: int=30, extra_pod_information: bool=False) -> Result:
		payload = [
			('appid', self._appid),
			('input', query),
			('units', 'nonmetric' if imperial else 'metric'),
			('scantimeout', 25)
		]
		if extra_pod_information:
			for i in WOLF_PODSTATES:
				payload.append(('podstate', i))
		for i in assumptions:
			payload.append(('assumption', i))
		async with session.get(self._server, params=payload, timeout=timeout) as result:
			result.raise_for_status()
			xml = await result.text()
		doc = xmltodict.parse(xml)
		result = Result(doc['queryresult'])
		if download_images:
			await result.download_images(session)
		return result


async def download_image(session, url):
	# print('Downloading', url)
	async with session.get(url, timeout = 20) as req:
		req.raise_for_status()
		# print('Completed  ', url)
		fo = io.BytesIO(await req.read())
		return PIL.Image.open(fo).convert('RGBA')


def listify(x):
	''' Wraps an object in a list if it is not already a list '''
	if not isinstance(x, list):
		return [x]
	return x


# async def web_get_text_multiple_attempts(session, server, payload, timeout, attempts = 2):
# 	while attempts > 0:
# 		try:
# 			async with session.get(server, params = payload, timeout = timeout) as result:
# 				result.raise_for_status()
# 				return await result.text()
# 		except Exception:
# 			attempts -= 1
# 			if attempts == 0:
# 				raise RequestFailed
# 	raise Exception('This point of the code should never have been reached.')


class Assumptions:

	def __init__(self, qr=[]):
		self.as_text = []
		self.emoji_count = 0
		self.emoji_to_code = {}
		self.count = 0
		self.count_unknown = 0
		self.count_known = 0
		for i in qr:
			self.add_assumption(i)

	def to_json(self):
		return {
			'as_text': self.as_text,
			'emoji_count': self.emoji_count,
			'emoji_to_code': self.emoji_to_code,
			'count': self.count,
			'count_unknown': self.count_unknown
		}

	@staticmethod
	def from_json(json):
		new = Assumptions()
		new.as_text = json['as_text']
		new.emoji_count = json['emoji_count']
		new.emoji_to_code = json['emoji_to_code']
		new.count = json['count']
		new.count_unknown = json['count_unknown']
		return new

	def get_emoji(self, index, default = None):
		if 0 <= index < len(ASSUMPTION_EMOJI):
			return ASSUMPTION_EMOJI[index]
		return default

	def use_emoji(self, code):
		emoji = self.get_emoji(self.emoji_count, UNKNOWN_EMOJI)
		self.emoji_count += 1
		if emoji != UNKNOWN_EMOJI:
			self.emoji_to_code[emoji] = code
		return emoji

	def add_assumption(self, assumption):
		self.count += 1
		self.count_known += 1
		values = listify(assumption.get('value', []))
		assumption_type = assumption['@type']
		print('Processing assumption of type', assumption_type)
		result = None
		template = assumption.get('@template', 'Assuming ${desc1}. Use ${desc2} instead.').replace('${', '{').replace('\\"', '"')
		if assumption_type in {'Clash', 'Unit', 'Function', 'NumberBase'}:
			# typing.List of alternatives on a single line. "{word} is {description}"
			optext_array = []
			for o in values[1:]:
				description = o['@desc'].strip()
				emoji = self.use_emoji(o['@input'])
				line = '{} `{}`'.format(emoji, description)
				optext_array.append(line)
			result = template.format(
				word = assumption.get('@word', '@word'),
				desc1 = values[0].get('@desc', '@desc'),
				desc2 = ' or '.join(optext_array)
			)
		elif assumption_type == 'MultiClash':
			# Uses only substitution. Unique
			sub_values = {}
			word = 'error'
			for i, o in enumerate(values):
				emoji = '' if i == 0 else self.use_emoji(o['@input']) + ' '
				word = o['@word'] or word
				sub_values['word' + str(i + 1)] = word
				sub_values['desc' + str(i + 1)] = emoji + codify(o['@desc'])
			result = template.format(**sub_values)
		elif assumption_type in {'SubCategory', 'Attribute', 'TideStation'}:
			# typing.List of alternatives on different lines. "Assuming {desc}"
			optext_array = []
			for o in values[1:]:
				emoji = self.use_emoji(o['@input'])
				line = ' - Use {} `{}` instead'.format(emoji, o['@desc'].strip())
				optext_array.append(line)
			result = 'Assuming {}.\n{}'.format(
				values[0]['@desc'],
				'\n'.join(optext_array)
			)
		elif assumption_type in {'DateOrder', 'CoordinateSystem'}:
			# typing.List of alternatives on same line. No {word}
			optext_array = []
			for o in values[1:]:
				description = o['@desc'].strip()
				emoji = self.use_emoji(o['@input'])
				line = '{} `{}`'.format(emoji, description)
				optext_array.append(line)
			result = 'Assuming {}. Use {} instead.'.format(
				values[0]['@desc'],
				' or '.join(optext_array)
			)
		elif assumption_type in {'MortalityYearDOB', 'typing.ListOrNumber', 'MixedFraction', 'AngleUnit', 'TimeAMOrPM', 'I', 'typing.ListOrTimes'}:
			# Only two option. May or may not have {word}.
			v = values[1]
			sub_values = {
				'word': assumption.get('@word', ''),
				'desc1': values[0]['@desc'],
				'desc2': '{} `{}`'.format(self.use_emoji(v['@input']), v['@desc'])
			}
			result = template.format(**sub_values)
		else:
			self.count_known -= 1
			self.count_unknown += 1
			result = 'Unknown assumption type `{}`'.format(assumption_type)
		assert(result is not None)
		self.as_text.append(result)

	def __str__(self):
		return '\n'.join(self.as_text)


class Section:

	def __init__(self, pod):
		self.title = pod.get('@title') # type: str
		self.id = pod.get('@id') # type: str
		subpods = listify(pod.get('subpod', []))
		self.plaintext = ' '.join(subpod.get('plaintext') or '' for subpod in subpods) # type: str
		self._urls = list(subpod['img']['@src'] for subpod in subpods)
		self._images = [None] * len(self._urls) # type: typing.List[typing.Optional[PIL.Image.Image]]
		# Just a logging thing
		for i in listify(pod.get('states', {}).get('state', [])):
			if i['@input'] not in ALL_PODSTATES:
				print('Found a new podstate:', i['@name'], i['@input'])

	def __getitem__(self, key):
		v = self._images[key]
		if v is None:
			raise NoImageError
		return v

	def __len__(self):
		return len(self._urls)

	async def download_image(self, session, index):
		image = await download_image(session, self._urls[index])
		self._images[index] = image

	def get_futures(self, session):
		futures = [self.download_image(session, i) for i in range(len(self._urls))]
		return asyncio.gather(*futures)

	def __repr__(self):
		return f'Section(title={self.title}, id={self.id}, plaintext={self.plaintext}, _urls={self._urls}, _images={self._images})'
