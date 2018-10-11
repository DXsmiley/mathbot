import random
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
from queuedict import QueueDict
from open_relative import *
from discord.ext.commands import command
from utils import is_private, MessageEditGuard

core.help.load_from_file('./help/latex.md')


LATEX_SERVER_URL = 'http://rtex.probablyaweb.site/api/v2'


# Load data from external files

def load_template():
	with open_relative('template.tex', encoding = 'utf-8') as f:
		raw = f.read()
	# Remove any comments from the template
	cleaned = re.sub(r'%.*\n', '', raw)
	return cleaned

TEMPLATE = load_template()

with open_relative('replacements.json', encoding = 'utf-8') as _f:
	repl_json = _f.read()
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


class LatexModule:

	def __init__(self, bot):
		self.bot = bot

	@command(aliases=['latex', 'rtex'])
	@core.settings.command_allowed('c-tex')
	async def tex(self, context, *, latex=''):
		if latex == '':
			await context.send('Type `=help tex` for information on how to use this command.')
		else:
			await self.handle(context.message, latex)

	@command(aliases=['wtex'])
	@core.settings.command_allowed('c-tex')
	async def texw(self, context, *, latex=''):
		if latex == '':
			await context.send('Type `=help tex` for information on how to use this command.')
		else:
			await self.handle(context.message, latex, wide=True)

	async def on_message_discarded(self, message):
		if not message.author.bot and message.content.count('$$') >= 2 and not message.content.startswith('=='):
			if is_private(message.channel) or (await self.bot.settings.resolve_message('c-tex', message) and await self.bot.settings.resolve_message('f-inline-tex', message)):
				latex = extract_inline_tex(message.clean_content)
				if latex != '':
					await self.handle(message, latex, centre=False)

	async def handle(self, message, latex, *, centre=True, wide=False):
		print(f'LaTeX - {message.author} - {latex}')
		colour_back, colour_text = await self.get_colours(message.author)
		# Content replacement has to happen last in case it introduces a marker
		latex = TEMPLATE.replace('#COLOUR',  colour_text) \
		                .replace('#PAPERTYPE', 'a2paper' if wide else 'a5paper') \
		                .replace('#BLOCK', 'gather*' if centre else 'flushleft') \
		                .replace('#CONTENT', process_latex(latex))
		await self.render_and_reply(message, latex, colour_back)

	async def render_and_reply(self, message, latex, colour_back):
		with MessageEditGuard(message, message.channel, self.bot) as guard:
			async with message.channel.typing():
				try:
					render_result = await generate_image_online(latex, colour_back)
				except asyncio.TimeoutError:
					await guard.send(LATEX_TIMEOUT_MESSAGE)
				except RenderingError:
					await guard.send('Rendering failed. Check your code. You can edit your existing message if needed.')
				else:
					await guard.send(file=discord.File(render_result, 'latex.png'))
					await self.bot.advertise_to(message.author, message.channel, guard)

	async def get_colours(self, user):
		colour_setting = await self.bot.keystore.get('p-tex-colour', str(user.id)) or 'dark'
		if colour_setting == 'light':
			return 'ffffff', '202020'
		elif colour_setting == 'dark':
			return '36393E', 'f0f0f0'
		# Fallback in case of other weird things
		return '36393E', 'f0f0f0'


async def generate_image_online(latex, colour_back):
	payload = {
		'format': 'png',
		'code': latex.strip(),
	}
	async with aiohttp.ClientSession() as session:
		try:
			async with session.post(LATEX_SERVER_URL, json=payload, timeout=8) as loc_req:
				loc_req.raise_for_status()
				jdata = await loc_req.json()
				if jdata['status'] == 'error':
					raise RenderingError
				filename = jdata['filename']
			# Now actually get the image
			async with session.get(LATEX_SERVER_URL + '/' + filename, timeout=3) as img_req:
				img_req.raise_for_status()
				fo = io.BytesIO(await img_req.read())
				image = PIL.Image.open(fo).convert('RGBA')
		except aiohttp.client_exceptions.ClientResponseError:
			raise RenderingError
	border_size = 4
	colour_back = imageutil.hex_to_tuple(colour_back)
	width, height = image.size
	backing = imageutil.new_monocolour((width + border_size * 2, height + border_size * 2), colour_back)
	backing.paste(image, (border_size, border_size), image)
	fobj = io.BytesIO()
	backing.save(fobj, format='PNG')
	fobj = io.BytesIO(fobj.getvalue())
	return fobj


def extract_inline_tex(content):
	parts = iter(content.split('$$'))
	latex = ''
	try:
		while True:
			word = next(parts)
			if word != '':
				latex += word.replace('#', '\\#') \
						     .replace('$', '\\$') \
						     .replace('%', '\\%')
				latex += ' '
			word = next(parts)
			if word != '':
				latex += '$\\displaystyle {}$ '.format(word.strip('`'))
	except StopIteration:
		pass
	return latex.rstrip()


def process_latex(latex):
	latex = latex.replace('`', ' ').strip(' \n')
	if latex.startswith('tex'):
		latex = latex[3:].strip('\n')
	for key, value in TEX_REPLACEMENTS.items():
		if key in latex:
			latex = latex.replace(key, value)
	return latex


def setup(bot):
	bot.add_cog(LatexModule(bot))
