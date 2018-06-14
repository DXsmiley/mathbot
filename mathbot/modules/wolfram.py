''' 

	Wolfram module

	Enables users to query Wolfram|Alpha.

	Commands:
		=wolf <query>
		=pup <query>

'''

import collections
import urllib.parse
import re
import itertools
import typing

import asyncio
import aiohttp
import discord
import PIL
import PIL.Image
import PIL.ImageOps
import PIL.ImageDraw
import PIL.ImageFont
import xml

import safe
import wolfapi
import wordfilter
import core.help
import core.module
import core.handles
import core.settings
import core.keystore
import core.parameters
from imageutil import *


core.help.load_from_file('./help/wolfram.md')

ERROR_MESSAGE_NO_RESULTS = """Wolfram|Alpha didn't send a result back.
Maybe your query was malformed?
"""

ERROR_MESSAGE_TIMEOUT = """Wolfram|Alpha query timed out.
Maybe you should try again?

If this error keeps recurring, you should report it to DXsmiley on the \
official MathBot server: https://discord.gg/JbJbRZS
"""

ERROR_MESSAGE_ACCOUNT_BLOCKED = """MathBot has exceeded the total number of \
Wolfram|Alpha queries it is allowed to make in one month.

You should report this error to DXsmiley on the official MathBot \
server: https://discord.gg/JbJbRZS
"""

FOOTER_LINK = """\
Data sourced from Wolfram|Alpha: <http://www.wolframalpha.com/input/?{query}>
Do more with Wolfram|Alpha Pro: <http://www.wolframalpha.com/pro/>
"""

IGNORE_MESSAGE_SERVER = """\
The bot is already processing a Wolfram|Alpha query for this server.
Try again in a moment.
"""

IGNORE_MESSAGE_DM = """\
The bot is already processing a Wolfram|Alpha query for you.
Please wait for it to finish before making another one.
"""

PERMS_FAILURE = '''\
I don't have permission to upload images here :frowning:
The owner of this server should be able to fix this issue.
'''

REACTION_PERM_FAILURE = '''\
I don't have permission to add reactions here :frowning:
The owner of this server should be able to fix this issue.
'''

FILTER_FAILURE = '''\
**That query contains one or more banned words and will not be run.**
The owner of this server has the power to turn this off.
Alternatively, you can make the query by messaging this bot directly.
Questions and requests should be directed to <@133804143721578505> on the official MathBot server: https://discord.gg/JbJbRZS
'''

NO_API_ERROR = '''
No key was supplied for the Wolfram|Alpha API.

If you're trying to set the bot up for development, see README.md for information on how to do this.
'''

RERUN_EMOJI = '🔄'
EXPAND_EMOJI = '\U000025B6' # ▶️
MAX_REACTIONS_IN_MESSAGE = 18

ASSUMPTIONS_MADE_MESSAGE = \
	'**Assumptions were made**\nPress {} to show them.\n\n'.format(EXPAND_EMOJI)

api_key = core.parameters.get('wolfram key')
api = None
if api_key is not None:
	api = wolfapi.Client(api_key)

server_locks = set() # type: typing.Set[typing.Any]
dm_locks = set() # type: typing.Set[typing.Any]


class AssumptionDataScope:

	def __init__(self, message: discord.Message, client: discord.Client) -> None:
		# self.message_id = message.id
		self.client = client
		self.data = None
		self.message = message

	async def __aenter__(self):
		self.data = await core.keystore.get_json('wolfram', 'message', self.message.id)
		if self.data is not None:
			self.data['assumptions'] = wolfapi.Assumptions.from_json(self.data['assumptions'])
			# chan = self.client.get_channel(self.data['channel id'])
			# self.data['message'] = self.client.get_message(chan, self.message['message id'])
			self.data['message'] = self.message
		return self.data

	async def __aexit__(self, exc_type, exc, tb):
		if self.data is not None:
			self.data['assumptions'] = self.data['assumptions'].to_json()
			del self.data['message']
			await core.keystore.set_json('wolfram', 'message', self.message.id, self.data, expire = 60 * 60 * 30)


# Dummy message. This is a sign that I need to work on the settings module somewhat.
class Dummy:
	def __init__(self, channel):
		self.channel = channel
		self.server = channel.server


class WolframModule(core.module.Module):

	# sent_footer_messages = {}

	@core.handles.command('wolf', '*', perm_setting='c-wolf')
	async def command_wolf(self, msg, query):
		if api is None:
			await self.send_message(msg.channel, NO_API_ERROR, blame=msg.author)
		elif query in ['', 'help']:
			return core.handles.Redirect('help wolfram')
		elif not msg.channel.is_private and not has_required_perms(msg.channel, msg.server.me):
			await self.send_message(msg.channel, PERMS_FAILURE, blame=msg.author)
		else:
			await self.lock_wolf(msg.channel, msg.author, query)

	@core.handles.command('pup', '*', perm_setting='c-wolf')
	async def command_pup(self, msg, query):
		if api is None:
			await self.send_message(msg.channel, NO_API_ERROR, blame=msg.author)
		elif query in ['', 'help']:
			return core.handles.Redirect('help wolfram')
		elif not msg.channel.is_private and not has_required_perms(msg.channel, msg.server.me):
			await self.send_message(msg.channel, PERMS_FAILURE, blame=msg.author)
		else:
			await self.lock_wolf(msg.channel, msg.author, query, pup=True)

	@core.handles.add_reaction(RERUN_EMOJI)
	async def rerun_rection(self, reaction, user):
		async with AssumptionDataScope(reaction.message, self.client) as data:
			if data is not None and not data['used'] and data['blame'] == user.id:
				if await core.settings.get_setting(reaction.message, 'c-wolf'): # Make sure it's still allowed here...
					assumptions_to_use = list(filter(bool, [
						data['assumptions'].emoji_to_code.get(i.emoji)
						for i in reaction.message.reactions
						if isinstance(i.emoji, str) and i.emoji in wolfapi.ASSUMPTION_EMOJI and i.count > 1
					]))
					channel = reaction.message.channel
					print('Rerunning query:', data['query'])
					if len(assumptions_to_use) == 0:
						print('   with no assumptions!?')
						if data['no change warning'] == False:
							await self.send_message(channel, "Why would you re-run a query without changing the assumptions? :thinking:", blame = user)
						data['no change warning'] = True
					else:
						print('With assumptions')
						for i in assumptions_to_use:
							print('    -', i)
						if not channel.is_private and not has_required_perms(channel, reaction.message.server.me):
							await self.send_message(message, PERMS_FAILURE)
							data['used'] = True
						elif await self.lock_wolf(channel, user, data['query'], assumptions = assumptions_to_use):
							data['used'] = True

	async def lock_wolf(self, channel, blame, query, assumptions = [], pup = False):
		lock_id = blame.id if channel.is_private else channel.server.id
		lock_set = dm_locks if channel.is_private else server_locks
		did_work = False
		if lock_id not in lock_set:
			lock_set.add(lock_id)
			did_work = True
			try:
				await self.answer_query(query, channel, blame, assumptions = assumptions, small=pup)
			finally:
				lock_set.remove(lock_id)
		else:
			await self.send_message(
				channel,
				IGNORE_MESSAGE_DM if channel.is_private else IGNORE_MESSAGE_SERVER,
				blame = blame
			)
		return did_work

	async def answer_query(self, query, channel, blame, assumptions=[], small=False, debug = False):
		safe.sprint('wolfram|alpha :', blame.name, ':', query)
		await self.send_typing(channel)
		enable_filter = False
		if not channel.is_private:
			enable_filter = await core.settings.resolve('f-wolf-filter', channel, channel.server, default = 'nsfw' not in channel.name)
		if enable_filter and wordfilter.is_bad(query):
			await self.send_message(channel, FILTER_FAILURE, blame=blame)
			return
		try:
			print('Making request')
			units = await core.keystore.get('p-wolf-units:' + str(blame.id))
			result = await api.request(query, assumptions, imperial=(units == 'imperial'), debug=debug)
		except (wolfapi.WolframError, wolfapi.WolframDidntSucceed):
			await self.send_message(channel, ERROR_MESSAGE_NO_RESULTS, blame=blame)
		except asyncio.TimeoutError:
			print('W|A timeout:', query)
			await self.send_message(channel, ERROR_MESSAGE_TIMEOUT.format(query), blame=blame)
		except aiohttp.ClientError as error:
			print('Wolf: HTTP processing error:', error.message)
			await self.send_message(channel, 'The server threw an error. Try again in a moment.', blame=blame)
		except xml.parsers.expat.ExpatError as error:
			print('Wolf: XML processing error:', error)
			await self.send_message(channel, 'The server returned some malformed data. Try again in a moment.', blame=blame)
		else:

			if len(result.sections) == 0:
				await self.send_message(channel, ERROR_MESSAGE_NO_RESULTS, blame = blame)
				return

			is_dark = (await core.keystore.get('p-tex-colour:' + blame.id)) == 'dark'

			sections_reduced = result.sections if not small else list(
				cleanup_section_list(
					itertools.chain(
						[find_first(section_is_input, result.sections, None)],
						list(filter(section_is_important, result.sections))
						or [find_first(section_is_not_input, result.sections, None)]
					)
				)
			)

			# Post images
			for img in process_images(sections_reduced, is_dark):
				await self.send_image(channel, img, 'result.png', blame=blame)
				await asyncio.sleep(1.05)

			embed, show_assuptions = await self.format_adm(channel, blame, query, result.assumptions, small)

			posted = await self.send_message(channel, embed=embed, blame=blame)

			if not small and show_assuptions:
				try:
					await self.add_reaction_emoji(posted, result.assumptions)
					payload = {
						'assumptions': result.assumptions.to_json(),
						'query': query,
						'used': False,
						'blame': blame.id,
						'channel id': posted.channel.id,
						'message id': posted.id,
						'no change warning': False
					}
					await core.keystore.set_json('wolfram', 'message', str(posted.id), payload, expire = 60 * 60 * 24)
				except discord.errors.Forbidden:
					await self.send_message(channel, REACTION_PERM_FAILURE, blame=blame)

			print('Done.')

	@staticmethod
	async def format_adm(channel, blame, query, assuptions, small):
		embed = discord.Embed(
			title='Do more with Wolfram|Alpha pro',
			url='http://www.wolframalpha.com/pro/'
		)
		if not channel.is_private and await core.settings.resolve('f-wolf-mention', channel, channel.server):
			embed.add_field(name='Query made by', value=blame.mention)
		if assuptions.count > 0 and len(str(assuptions)) <= 800:
			embed.add_field(name='Assumptions', value=str(assuptions))
			return embed, True
		return embed, False

	async def add_reaction_emoji(self, message, assumptions):
		''' Adds assumption emoji to a message. '''
		try:
			if assumptions.emoji_count <= MAX_REACTIONS_IN_MESSAGE:
				for i in range(assumptions.emoji_count):
					emoji = assumptions.get_emoji(i)
					if emoji:
						# Whenever we add a reaction, it automatically exhausts the bucket.
						# This seems strange, but whatever.
						await self.client.add_reaction(message, emoji)
						await asyncio.sleep(0.3)
			await self.client.add_reaction(message, RERUN_EMOJI)
		except discord.errors.NotFound:
			# The message could potentially get deleted part way through
			# adding emoji. If this happens we should ignore it.
			print('Message disappeared in the middle of adding reactions.')


SHOULD_ERROR = object()


def find_first(predicate, iterator, default = SHOULD_ERROR):
	''' Return the first item from iterator that conforms to the predicate '''
	for i in iterator:
		if predicate(i):
			return i
	if default is SHOULD_ERROR:
		raise ValueError
	return default


MAX_GROUP_HEIGHT = 300
IMAGE_Y_PADDING = 10


def process_images(sections, is_dark):
	strip = sections_to_image_strip(sections)
	strip = retheme_images(strip) if is_dark else map(lambda x: x[0], strip)
	background_colour = hex_to_tuple_a('36393EFF') if is_dark else hex_to_tuple_a('FFFFFFFF')	
	for img in conjoin_image_results(strip, background_colour):
		img = paste_to_background(img, background_colour)
		yield img


# Result is a list of tuples of the form: (image, section, is_title)
def sections_to_image_strip(sections):
	for section in sections:
		yield (textimage(section.title), section, True)
		for image in section._images:
			yield (trim_image(image), section, False)


def retheme_images(strip):
	''' Takes a strip of (image, section, is_title) things and
		recolours the ones that need to me
	'''
	for image, section, is_title in strip:
		if is_title or (not re.search(r'^Image:|:Colou?rData$', section.id)):
			image_recolour_to_dark_theme(image)
		yield image


def conjoin_image_results(images, background_colour = (255, 255, 255, 0)):
	''' Takes a list of images and stitches some of them together to reduce the number
		of images that need to be sent - but prevents individual images from being too tall
	'''
	for group in group_images(images):
		height = sum(map(lambda x: x.height + IMAGE_Y_PADDING, group))
		width = max(map(lambda x: x.width + 10, group))
		result = PIL.Image.new('RGBA', (width, height), background_colour)
		y = 0
		for i in group:
			result.paste(i, (5, y, 5 + i.width, y + i.height))
			y += i.height + IMAGE_Y_PADDING
		yield result


def group_images(images):
	''' Takes a sqeunce of images and groups them such that no group is too high '''
	temp = []
	height = 0
	for i in images:
		if height != 0 and height + i.height + IMAGE_Y_PADDING > MAX_GROUP_HEIGHT:
			yield temp
			temp = []
			height = 0
		temp.append(i)
		height += i.height + IMAGE_Y_PADDING
	if len(temp) > 0:
		yield temp


def has_required_perms(channel, member):
	if channel.is_private:
		return True
	perms = channel.permissions_for(member)
	return perms.attach_files


def image_recolour_to_dark_theme(img):
	''' Takes an image and converts it to the dark theme '''
	image_invert(img)
	image_scale_channels(img, hex_to_tuple('36393E'), hex_to_tuple('FFFFFF'))


def section_is_input(s):
	''' Determine if a section is an input section '''
	return s.title.lower() in [
		'input',
		'input interpretation'
	]


def section_is_not_input(s):
	''' Determine if a section is NOT an input section '''
	return not section_is_input(s)


def section_is_important(s):
	''' Determine if a section is important or not '''
	return s.title.lower() in [
		'solution',
		'result',
		'biological properties',
		'image',
		'color swatch',
		'related colors'
	]


def cleanup_section_list(items):
	''' Takes a list of sections and removes any that
		are None or any that appear twice.
	'''
	seen = set()
	for i in items:
		if i is not None and id(i) not in seen:
			seen.add(id(i))
			yield i
