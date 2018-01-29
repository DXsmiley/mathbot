import random
import requests
import os
import safe
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import io
import core.settings
import urllib
import aiohttp
import asyncio
import traceback
import re
import imageutil
import core.help
import advertising
import discord
import json
from open_relative import *


core.help.load_from_file('./help/latex.md')


LATEX_SERVER_URL = 'http://rtex.probablyaweb.site/api/v2'


# Load data from external files

def load_templates():
	raw = open_relative('template.tex', encoding = 'utf-8').read()
	# Remove any comments from the template
	cleaned = re.sub(r'%.*\n', '', raw)
	template = cleaned.replace('#BLOCK', 'gather*')
	t_inline = cleaned.replace('#BLOCK', 'flushleft')
	return template, t_inline

TEMPLATE, TEMPLATE_INLINE = load_templates()

repl_json = open_relative('replacements.json', encoding = 'utf-8').read()
TEX_REPLACEMENTS = json.loads(repl_json)


# Error messages

LATEX_TIMEOUT_MESSAGE = 'The renderer took too long to respond.'

PERMS_FAILURE = '''\
I don't have permission to upload images here :frowning:
The owner of this server should be able to fix this issue.
'''

DELETE_PERMS_FAILURE = '''\
The bot has been set up to delete `=tex` command inputs.
It requires the **manage messages** permission in order to do this.
'''


class RenderingError(Exception):
	pass


class LatexModule(core.module.Module):

	def __init__(self):
		# Keep track of recently fulfilled requests
		# Holds dictionaries of
		# {
		# 	'template': (either 'normal' or 'inline', depending on what was used),
		# 	'message': the ID of the _output_ message
		# }
		self.connections = {}

	@core.handles.command('tex latex rtex', '*', perm_setting = 'c-tex')
	async def command_latex(self, message, latex):
		if latex == '':
			await self.send_message(message.channel, 'Type `=help tex` for information on how to use this command.', blame = message.author)
		elif not has_required_perms(message.channel):
			await self.send_message(message.channel, PERMS_FAILURE, blame = message.author)
		else:
			# print('Handling command:', latex)
			await self.handle(message, latex, 'normal')
			if await core.settings.get_setting(message, 'f-delete-tex'):
				await asyncio.sleep(10)
				try:
					await self.client.delete_message(message)
				except discord.errors.NotFound:
					pass
				except discord.errors.Forbidden:
					await self.send_message(message.channel, DELETE_PERMS_FAILURE, blame = message.author)

	@command_latex.edit(require_before = False, require_after = True)
	async def handle_edit(self, before, after, latex):
		if latex != '' and before.content != after.content:
			blob = self.connections.get(before.id, {'template': 'normal'})
			try:
				await self.client.delete_message(blob['message'])
			except Exception:
				pass
			# print('Handling edit:', latex)
			await self.handle(after, latex, blob.get('template'))

	@core.handles.on_message()
	async def inline_latex(self, message):
		# The testing bot should not be ignored
		ignore = message.author.bot and message.author.id != '309967930269892608'
		server_prefix = await core.settings.get_server_prefix(message)
		if not ignore and not message.content.startswith(server_prefix) and message.content.count('$$') >= 2:
			if message.channel.is_private or (await core.settings.get_setting(message, 'c-tex') and await core.settings.get_setting(message, 'f-inline-tex')):
				latex = extract_inline_tex(message.clean_content)
				if latex != '':
					await self.handle(message, latex, 'inline')

	@core.handles.on_edit()
	async def inline_edit(self, before, after):
		server_prefix = await core.settings.get_server_prefix(message)
		if not after.content.startswith(server_prefix) and after.content.count('$$') >= 2 and before.content != after.content:
			if after.channel.is_private or (await core.settings.get_setting(after, 'c-tex') and await core.settings.get_setting(after, 'f-inline-tex')):
				blob = self.connections.get(before.id, {'template': 'inline'})
				try:
					await self.client.delete_message(blob['message'])
				except Exception:
					pass
				latex = extract_inline_tex(after.clean_content)
				if latex != '':
					await self.handle(after, latex, blob.get('template'))

	async def handle(self, message, latex, template):
		safe.sprint('Latex ({}, {}) : {}'.format(message.author.name, template, latex))
		await self.client.send_typing(message.channel)

		colour_back, colour_text = await get_colours(message)

		tpl = ({'normal': TEMPLATE, 'inline': TEMPLATE_INLINE})[template]

		latex = tpl.replace(
			'#COLOUR', colour_text
		).replace(
			'#CONTENT', process_latex(latex)
		)

		sent_message = await self.render_and_reply(message, latex, colour_back, colour_text)
		if sent_message != None:
			self.connections[message.id] = {
				'message': sent_message,
				'template': template
			}

	async def render_and_reply(self, message, latex, colour_back, colour_text):
		get_timestamp = lambda : message.edited_timestamp or message.timestamp
		original_timestamp = get_timestamp()
		try:
			render_result = await generate_image_online(latex, colour_back = colour_back, colour_text = colour_text)
		except asyncio.TimeoutError:
			return await self.send_message(message.channel, LATEX_TIMEOUT_MESSAGE, blame = message.author)
		except RenderingError:
			print('Rendering Error')
			if get_timestamp() == original_timestamp:
				return await self.send_message(message.channel,
					'Rendering failed. Check your code. You can edit your existing message if needed.',
					blame = message.author
				)
		else:
			print('Success!')
			content = None
			if await advertising.should_advertise_to(message.author, message.channel):
				content = 'Support the bot on Patreon: <https://www.patreon.com/dxsmiley>'
			# If the query message has been updated in this time, don't post the (now out of date) result
			if get_timestamp() == original_timestamp:
				return await self.send_image(message.channel, render_result, fname = 'latex.png', blame = message.author, content = content)


async def generate_image_online(latex, colour_back = None, colour_text = '000000'):
	payload = {
		'format': 'png',
		'code': latex.strip(),
	}
	async with aiohttp.ClientSession() as session:
		try:
			async with session.post(LATEX_SERVER_URL, json = payload, timeout = 8) as loc_req:
				loc_req.raise_for_status()
				jdata = await loc_req.json()
				# print('LOG:\n', jdata.get('log'))
				# print(jdata.get('status'))
				# print(jdata.get('description'))
				if jdata['status'] == 'error':
					# print(json.dumps(jdata))
					raise RenderingError
				filename = jdata['filename']
			# Now actually get the image
			async with session.get(LATEX_SERVER_URL + '/' + filename, timeout = 3) as img_req:
				img_req.raise_for_status()
				fo = io.BytesIO(await img_req.read())
				image = PIL.Image.open(fo).convert('RGBA')
		except aiohttp.client_exceptions.ClientResponseError:
			raise RenderingError
	if colour_back is not None:
		colour_back = imageutil.hex_to_tuple(colour_back)
		back = imageutil.new_monocolour(image.size, colour_back)
		back.paste(image, (0, 0), image)
		image = imageutil.add_border(back, 4, colour_back)
	return image


async def get_colours(message):
	colour_setting = await core.keystore.get('p-tex-colour', message.author.id) or 'dark'
	if colour_setting == 'light':
		return 'ffffff', '202020'
	elif colour_setting == 'dark':
		return '36393E', 'f0f0f0'
	# Fallback in case of other weird things
	return '36393E', 'f0f0f0'
	# raise ValueError('{} is not a valid colour scheme'.format(colour_setting))


def extract_inline_tex(content):
	parts = iter(content.split('$$'))
	latex = ''
	try:
		while True:
			word = next(parts)
			if word != '':
				latex += '{} '.format(
					word.replace('#', '\#')
						.replace('$', '\$')
						.replace('%', '\%')
				)
			word = next(parts)
			if word != '':
				latex += '$\displaystyle {}$ '.format(word.strip('`'))
	except StopIteration:
		pass
	return latex.rstrip()


def process_latex(latex):
	latex = latex.strip(' `\n')
	if latex.startswith('tex'):
		latex = latex[3:]
	for key, value in TEX_REPLACEMENTS.items():
		if key in latex:
			latex = latex.replace(key, value)
	return latex


def has_required_perms(channel):
	if channel.is_private:
		return True
	perms = channel.permissions_for(channel.server.me)
	return perms.attach_files
