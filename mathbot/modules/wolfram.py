import time
import shutil
import requests
import os
import safe
import asyncio
import collections
import urllib.parse
import PIL
import PIL.Image
import PIL.ImageOps
import PIL.ImageDraw
# import PIL.Draw
import PIL.ImageFont
import io
import wolfapi
# import skytrails
import gc
import traceback
import core.help
import core.module
import core.handles
import core.settings
import core.keystore
import core.parameters
import aiohttp
import json
import wordfilter
import discord
import xml
import re
import itertools

from imageutil import *

core.help.load_from_file('./help/wolfram.md')

ERROR_MESSAGE_NO_RESULTS = """Wolfram|Alpha didn't send a result back.
Maybe your query was malformed?
"""

ERROR_MESSAGE_FAILED = '''Failed to make the request.
Maybe you should try again?

If this error keeps recurring, you should report it to DXsmiley on the \
official MathBot server: https://discord.gg/JbJbRZS
'''

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

ASSUMPTIONS_MADE_MESSAGE = '**Assumptions were made**\nPress {} to show them.\n\n'.format(EXPAND_EMOJI)

api_key = core.parameters.get('wolfram key')
api = None
if api_key is not None:
	api = wolfapi.Client(api_key)

server_locks = set()
dm_locks = set()

def download_image(url):
	response = requests.get(url, stream = True)
	return PIL.Image.open(response.raw).convert('RGB')


MAX_GROUP_HEIGHT = 300
IMAGE_Y_PADDING = 10


def group_images(images):
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


def conjoin_image_results(images, background_colour = (255, 255, 255, 0)):
	for group in group_images(images):
		height = sum(map(lambda x: x.height + IMAGE_Y_PADDING, group))
		width = max(map(lambda x: x.width + 10, group))
		result = PIL.Image.new('RGBA', (width, height), background_colour)
		y = 0
		for i in group:
			result.paste(i, (5, y, 5 + i.width, y + i.height))
			y += i.height + IMAGE_Y_PADDING
		yield result
		# await send_image(message.channel, result, 'result.png', blame = message.author)
		# await asyncio.sleep(1.05)


# Result is a list of tuples of the form: (image, section, is_title)
def sections_to_image_strip(sections):
	result = []
	for section in sections:
		result.append((textimage(section.title), section, True))
		for image in section.images:
			# replace_colour(image, (255, 255, 255, 255), (255, 255, 255, 0))
			# result.append(image)
			result.append((trim_image(image), section, False))
	return result


def has_required_perms(channel, member):
	if channel.is_private:
		return True
	perms = channel.permissions_for(member)
	return perms.attach_files


def image_recolour_to_dark_theme(img):
	image_invert(img)
	image_scale_channels(img, hex_to_tuple('36393E'), hex_to_tuple('FFFFFF'))


def retheme_images(strip, processor):
	for image, section, is_title in strip:
		if is_title or (not re.search(r'^Image:|:Colou?rData$', section.id)):
			processor(image)
		yield image


class AssumptionDataScope:

	def __init__(self, message, client):
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

	@core.handles.command('wolf', '*', perm_setting = 'c-wolf')
	async def command_wolf(self, message, query):
		if api is None:
			await self.send_message(message.channel, NO_API_ERROR, blame = message.author)
		elif query in ['', 'help']:
			return core.handles.Redirect('help wolfram')
		elif not message.channel.is_private and not has_required_perms(message.channel, message.server.me):
			await self.send_message(message.channel, PERMS_FAILURE, blame = message.author)
		else:
			await self.lock_wolf(message.channel, message.author, query)

	@core.handles.command('pup', '*', perm_setting = 'c-wolf')
	async def command_pup(self, message, query):
		if api is None:
			await self.send_message(message.channel, NO_API_ERROR, blame = message.author)
		elif query in ['', 'help']:
			return core.handles.Redirect('help wolfram')
		elif not message.channel.is_private and not has_required_perms(message.channel, message.server.me):
			await self.send_message(message.channel, PERMS_FAILURE, blame = message.author)
		else:
			await self.lock_wolf(message.channel, message.author, query, pup = True)

	@core.handles.add_reaction(RERUN_EMOJI)
	async def rerun_rection(self, reaction, user):
		print(self.shard_id, 'Rerun emoji')
		async with AssumptionDataScope(reaction.message, self.client) as data:
			print('1')
			if data is not None and not data['used'] and data['blame'] == user.id:
				print('2')
				if await core.settings.get_setting(reaction.message, 'c-wolf'): # Make sure it's still allowed here...
					print('3')
					assumptions_to_use = list(filter(bool, [
						data['assumptions'].emoji_to_code.get(i.emoji)
						for i in reaction.message.reactions
						if isinstance(i.emoji, str) and i.emoji in wolfapi.ASSUMPTION_EMOJI and i.count > 0
					]))
					print('Rerunning `{}` with assumptions `{}`'.format(data['query'], ', '.join(assumptions_to_use)))
					# Can only re-run each thing once.
					# TODO: Abstract this
					channel = reaction.message.channel
					if len(assumptions_to_use) == 0:
						if data['no change warning'] == False:
							await self.send_message(channel, "Why would you re-run a query without changing the assumptions? :thinking:", blame = user)
						data['no change warning'] = True
					elif not channel.is_private and not has_required_perms(channel, reaction.message.server.me):
						await self.send_message(channel, PERMS_FAILURE, blame = user)
						data['used'] = True
					elif await self.lock_wolf(channel, user, data['query'], assumptions = assumptions_to_use):
						data['used'] = True

	@core.handles.add_reaction(EXPAND_EMOJI)
	async def expand_assumptions(self, reaction, user):
		async with AssumptionDataScope(reaction.message, self.client) as data:
			if data is not None and data['hidden'] and data['blame'] == user.id:
				data['hidden'] = False
				assumption_text = self.get_assumption_text(data['assumptions'])
				text = data['message'].content.replace(ASSUMPTIONS_MADE_MESSAGE, assumption_text)
				await self.client.edit_message(data['message'], text)
				await self.add_reaction_emoji(data['message'], data['assumptions'])

	async def lock_wolf(self, channel, blame, query, assumptions = [], pup = False):
		lock_id = blame.id if channel.is_private else channel.server.id
		lock_set = dm_locks if channel.is_private else server_locks
		did_work = False
		if lock_id not in lock_set:
			lock_set.add(lock_id)
			did_work = True
			try:
				if pup:
					await self.answer_query_short(query, channel, blame)
				else:
					await self.answer_query(query, channel, blame, assumptions = assumptions)
			finally:
				lock_set.remove(lock_id)
				# A return statement in here swallows the exception.
		else:
			await self.send_message(
				channel,
				IGNORE_MESSAGE_DM if channel.is_private else IGNORE_MESSAGE_SERVER,
				blame = blame
			)
		return did_work

	async def answer_query_short(self, query, channel, blame):
		safe.sprint('wolfram|alpha :', blame.name, ':', query)
		await self.client.send_typing(channel)
		images = []
		text = []
		error = 0
		error_message = 'No details'
		enable_filter = False
		if not channel.is_private:
			enable_filter = await core.settings.resolve('f-wolf-filter', channel, default = 'nsfw' not in channel.name)
		if enable_filter and wordfilter.is_bad(query):
			await self.send_message(channel, FILTER_FAILURE, blame = blame)
			return
		try:
			print('Making request')
			result = await api.request(query, [], debug = False)
			print('Done?')
		except asyncio.TimeoutError:
			print('W|A timeout:', query)
			await self.send_message(channel, ERROR_MESSAGE_TIMEOUT, blame = blame)
		except aiohttp.ClientError as e:
			print('Wolf: HTTP processing error:', e.message)
			await self.send_message(channel, 'The server threw an error. Try again in a moment.', blame = blame)
		except xml.parsers.expat.ExpatError as e:
			print('Wolf: XML processing error:', e.message)
			await self.send_message(channel, 'The server returned some malformed data. Try again in a moment.', blame = blame)
		else:
			# print(json.dumps(result.sections, indent = 4))
			if len(result.sections) == 0:
				await self.send_message(channel, ERROR_MESSAGE_NO_RESULTS, blame = blame)
			elif result.did_fail:
				m = 'Something went wrong: {}'.format(result.error_text)
				await self.send_message(channel, m, blame = blame)
			else:
				# for i in result.sections:
				# 	print(' -', i.title)
				sections_reduced = list(cleanup_section_list(itertools.chain(
					[find_first(section_is_input, result.sections, None)],
					list(filter(section_is_important, result.sections))
					or [find_first(section_is_not_input, result.sections, None)]
				)))
				is_dark = ((await core.keystore.get('p-tex-colour', blame.id)) == 'dark')
				# Send the image results
				background_colour = hex_to_tuple_a('36393EFF' if is_dark else 'FFFFFFFF')
				strip = sections_to_image_strip(sections_reduced)
				if is_dark:
					strip = retheme_images(strip, image_recolour_to_dark_theme)
				else:
					strip = (i for i, _, _ in strip)
				for img in conjoin_image_results(strip, background_colour):
					img = paste_to_background(img, background_colour)
					await self.send_image(channel, img, 'result.png', blame = blame)
					await asyncio.sleep(1.05)
				# Text section
				adm = await self.format_adm(channel, blame, query, is_pup = True)
				posted = await self.send_message(channel, adm, blame = blame)
				print('Done.')

	async def answer_query(self, query, channel, blame, assumptions = [], debug = False):
		safe.sprint('wolfram|alpha :', blame.name, ':', query)
		await self.client.send_typing(channel)
		images = []
		text = []
		error = 0
		error_message = 'No details'
		# Dummy message. This is a sign that I need to work on the settings module somewhat.
		class Dummy:
			def __init__(self, channel):
				self.channel = channel
				self.server = channel.server
		enable_filter = False
		if not channel.is_private:
			enable_filter = await core.settings.resolve('f-wolf-filter', channel, default = 'nsfw' not in channel.name)
			# print(core.get_setting_context(Dummy(channel), 'f-wolf-filter', 'channel'))
			# print(core.get_setting_context(Dummy(channel), 'f-wolf-filter', 'server'))
			# print(enable_filter)
		if enable_filter and wordfilter.is_bad(query):
			await self.send_message(channel, FILTER_FAILURE, blame = blame)
			return
		try:
			print('Making request')
			result = await api.request(query, assumptions, debug = debug)
			print('Done?')
		except wolfapi.RequestFailed:
			await self.send_message(channel, ERROR_MESSAGE_FAILED, blame = blame)
		except asyncio.TimeoutError:
			print('W|A timeout:', query)
			await self.send_message(channel, ERROR_MESSAGE_TIMEOUT.format(query), blame = blame)
		except aiohttp.ClientError as e:
			print('Wolf: HTTP processing error:', e.message)
			await self.send_message(channel, 'The server threw an error. Try again in a moment.', blame = blame)
		except xml.parsers.expat.ExpatError as e:
			print('Wolf: XML processing error:', e)
			await self.send_message(channel, 'The server returned some malformed data. Try again in a moment.', blame = blame)
		else:
			if len(result.sections) == 0:
				await self.send_message(channel, ERROR_MESSAGE_NO_RESULTS, blame = blame)
			elif result.did_fail:
				m = 'Something went wrong: {}'.format(result.error_text)
				await self.send_message(channel, m, blame = blame)
			else:
				# Get theme setting (TODO: Don't construct this myself)
				key = 'p-tex-colour:' + blame.id
				theme = await core.keystore.get(key)
				is_dark = (theme == 'dark')
				# print('The theme:', theme)
				# Send the image results
				background_colour = hex_to_tuple_a('36393EFF') if is_dark else hex_to_tuple_a('FFFFFFFF')
				if not debug:
					strip = sections_to_image_strip(result.sections)
					strip = retheme_images(strip, image_recolour_to_dark_theme if is_dark else lambda x : None)
					for img in conjoin_image_results(strip, background_colour):
						img = paste_to_background(img, background_colour)
						# await self.send_image(channel, img, 'result.png', blame = blame)
						# if theme == 'dark':
						# 	image_recolour_to_dark_theme(img)
						await self.send_image(channel, img, 'result.png', blame = blame)
						await asyncio.sleep(1.05)
				# Text section
				textitems = []
				# Assumptions
				assumption_text = self.get_assumption_text(result.assumptions)
				hidden_assumptions = assumption_text.count('\n') > 5
				if hidden_assumptions:
					assumption_text = ASSUMPTIONS_MADE_MESSAGE
				textitems.append(assumption_text)
				# Tips
				if len(result.tips) > 0:
					textitems += [
						'**Tips**\n',
						'\n'.join(result.tips),
						'\n\n'
					]
				# Timeouts
				if len(result.timeouts) > 0:
					textitems += [
						'**Timeouts**\n',
						', '.join(result.timeouts),
						'\n\n'
					]
				textout_joined = ''.join(textitems)
				url = urllib.parse.urlencode({'i': query})
				# Determine if the footer should be long or short
				adm = await self.format_adm(channel, blame, query, False)
				output = textout_joined + adm
				too_long = False
				if len(output) >= 2000:
					too_long = True
					output = adm
				# Send the result
				posted = await self.send_message(channel, output, blame = blame)
				if result.assumptions.count - result.assumptions.count_unknown > 0 and not too_long:
					try:
						if hidden_assumptions:
							await self.client.add_reaction(posted, EXPAND_EMOJI)
						else:
							await self.add_reaction_emoji(posted, result.assumptions)
						payload = {
							'assumptions': result.assumptions.to_json(),
							'query': query,
							'used': False,
							'blame': blame.id,
							'channel id': posted.channel.id,
							'message id': posted.id,
							'no change warning': False,
							'hidden': hidden_assumptions
						}
						print(json.dumps(payload, indent = 4))
						# self.sent_footer_messages[str(posted.id)] = payload
						await core.keystore.set_json('wolfram', 'message', str(posted.id), payload, expire = 60 * 60 * 24)
						print(self.shard_id, 'Footer message id:', posted.id)
					except discord.errors.Forbidden:
						await self.send_message(channel, REACTION_PERM_FAILURE, blame = blame)
				# Complete!
				print('Done.')

	async def format_adm(self, channel, blame, query, is_pup = False):
		result = []
		url = urllib.parse.urlencode({'i': query})
		if not channel.is_private and await core.settings.resolve('f-wolf-mention', channel, channel.server):
			result.append('Query made by {}\n'.format(blame.mention))
		url = urllib.parse.urlencode({'i': query})
		result.append(FOOTER_LINK.format(query = url))
		if not is_pup:
			result.append('🐺 **Try out the new `=pup` command!** It\'s much more concise.\n')
		return ''.join(result)

	def get_assumption_text(self, assumptions):
		if assumptions.count == 0:
			return ''
		return '**Assumptions**\n{}\n\n'.format(str(assumptions))

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


def section_is_input(s):
	return s.title.lower() in [
		'input',
		'input interpretation'
	]


def section_is_not_input(s):
	return not section_is_input(s)


def section_is_important(s):
	return s.title.lower() in [
		'solution',
		'result',
		'biological properties',
		'image',
		'color swatch',
		'related colors'
	]


def cleanup_section_list(items):
	seen = set()
	for i in items:
		if i is not None and id(i) not in seen:
			seen.add(id(i))
			yield i
