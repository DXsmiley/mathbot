import aiohttp
import xmltodict
import json
import asyncio
import PIL
import PIL.Image
import io


italify = '*{}*'.format
boldify = '**{}**'.format
codify = '`{}`'.format


# ASSUMPTION_EMOJI = '🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿'
ASSUMPTION_EMOJI = '🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿'
UNKNOWN_EMOJI = '❔'


async def echo(x):
	return x


async def download_image(session, url):
	# print('Downloading', url)
	async with session.get(url, timeout = 20) as req:
		req.raise_for_status()
		# print('Completed  ', url)
		fo = io.BytesIO(await req.read())
		return PIL.Image.open(fo).convert('RGBA')


def listify(x):
	if not isinstance(x, list):
		return [x]
	return x


async def web_get_text_multiple_attempts(session, server, payload, timeout, attempts = 2):
	try:
		async with session.get(server, params = payload, timeout = timeout) as result:
			result.raise_for_status()
			return await result.text()
	except Exception:
		if attempts > 1:
			return await web_get_text_multiple_attempts(session, server, payload, timeout, attempts - 1)
		raise


class Assumptions:

	def __init__(self):
		self.as_text = []
		self.emoji_count = 0
		self.emoji_to_code = {}
		self.count = 0
		self.count_unknown = 0

	def to_json(self):
		return {
			'as_test': self.as_text,
			'emoji_count': self.emoji_count,
			'emoji_to_code': self.emoji_to_code,
			'count': self.count,
			'count_unknown': self.count_unknown
		}

	def from_json(json):
		new = Assumptions()
		new.as_text = json['as_test']
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
		values = listify(assumption.get('value', []))
		type = assumption['@type']
		print('Processing assumption of type', type)
		result = None
		template = assumption.get('@template', 'Assuming ${desc1}. Use ${desc2} instead.').replace('${', '{').replace('\\"', '"')
		if type in {'Clash', 'Unit', 'Function', 'NumberBase'}:
			# List of alternatives on a single line. "{word} is {description}"
			assumed = values[0]
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
		elif type == 'MultiClash':
			# Uses only substitution. Unique
			sub_values = {}
			word = 'error'
			for i, o in enumerate(values):
				description = o['@desc'].strip()
				emoji = '' if i == 0 else self.use_emoji(o['@input']) + ' '
				word = o['@word'] or word
				sub_values['word' + str(i + 1)] = word
				sub_values['desc' + str(i + 1)] = emoji + codify(o['@desc'])
			result = template.format(**sub_values)
		elif type in {'SubCategory', 'Attribute', 'TideStation'}:
			# List of alternatives on different lines. "Assuming {desc}"
			optext_array = []
			for o in values[1:]:
				emoji = self.use_emoji(o['@input'])
				line = ' - Use {} `{}` instead'.format(emoji, o['@desc'].strip())
				optext_array.append(line)
			result = 'Assuming {}.\n{}'.format(
				values[0]['@desc'],
				'\n'.join(optext_array)
			)
		elif type in {'DateOrder', 'CoordinateSystem'}:
			# List of alternatives on same line. No {word}
			assumed = values[0]
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
		elif type in {'MortalityYearDOB', 'ListOrNumber', 'MixedFraction', 'AngleUnit', 'TimeAMOrPM', 'I', 'ListOrTimes'}:
			# Only two option. May or may not have {word}.
			v = values[1]
			sub_values = {
				'word': assumption.get('@word', ''),
				'desc1': values[0]['@desc'],
				'desc2': '{} `{}`'.format(self.use_emoji(v['@input']), v['@desc'])
			}
			result = template.format(**sub_values)
		else:
			self.count_unknown += 1
			result = 'Unknown assumption type `{}`'.format(type)
		assert(result is not None)
		self.as_text.append(result)

	def __str__(self):
		return '\n'.join(self.as_text)


class Section:

	def __init__(self, title, id):
		self.title = title
		self.urls = []
		self.images = []
		self.id = id

	def add_image(self, url):
		self.urls.append(url)
		self.images.append(None)

	async def download_image(self, session, index):
		image = await download_image(session, self.urls[index])
		self.images[index] = image

	def get_futures(self, session):
		futures = [self.download_image(session, i) for i in range(len(self.urls))]
		return asyncio.gather(*futures)


class Result:

	def __init__(self, ):
		self.tips = []
		self.textout = []
		self.sections = []
		self.timeouts = []
		self.assumptions = Assumptions()
		self.did_fail = False
		self.error_text = []

	def add_data(self, qr):
		if qr['@error'] == 'true':
			self.did_fail = True
			self.error_text = qr['error'].get('@msg', '?')
			self.textout = [
				'**The server produced an error**',
				qr['error'].get('@msg', '?'),
				''
			]
		else:
			# Show the tips
			if qr['@success'] == 'false':
				if 'tips' in qr:
					for tip in listify(qr['tips']['tip']):
						self.tips.append(tip['@text'])
			# List the assumptions
			if 'assumptions' in qr:
				self.textout.append('**The following assumptions were made**')
				for assumption in listify(qr['assumptions']['assumption']):
					self.assumptions.add_assumption(assumption)
				self.textout += self.assumptions.as_text
				self.textout.append('')
			# List the pods
			for pod in listify(qr.get('pod', [])):
				section = Section(pod['@title'], pod.get('@id'))
				for sub in listify(pod['subpod']):
					section.add_image(sub['img']['@src'])
				self.sections.append(section)
			# List the things that timed out
			self.timeouts = list(filter(lambda x : x != '', qr.get('@timedout', '').split(',')))
			# If there's nothing, give an error

	async def download(self, session):
		futures = [i.get_futures(session) for i in self.sections]
		await asyncio.gather(*futures)

	def __str__(self):
		self.result = []
		return '\n'.join(self.result)


class Client:

	def __init__(self, appid, server = None):
		self.appid = appid
		self.server = server or r'https://api.wolframalpha.com/v2/query' #?input=pi&appid=XXXX

	async def request(self, query, assumptions, debug = False):
		print('Inside the request function!')
		print(query, assumptions)
		result = Result()
		async with aiohttp.ClientSession() as session:
			payload = [
				('appid', self.appid),
				('input', query)
			] + [
				('assumption', i) for i in assumptions
			]
			# print(json.dumps(payload, indent = 4))
			xml = await web_get_text_multiple_attempts(session, self.server, payload, 30, 2)
			# print(xml)
			doc = xmltodict.parse(xml)
			# print(json.dumps(doc, indent = 4))
			qr = doc['queryresult']
			result.add_data(qr)
			await result.download(session)
			# print(futures)
			# results = await asyncio.gather(*futures)
			# print(results)
		return result
