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
from discord.ext.commands import command, Cog
from utils import is_private, MessageEditGuard
from contextlib import suppress

core.help.load_from_file('./help/latex.md')


LATEX_SERVER_URL = 'http://rtex.probablyaweb.site/api/v2'
DELETE_EMOJI = '🗑'


# Load data from external files

def load_template():
	with open_relative('template.tex', encoding = 'utf-8') as f:
		raw = f.read()
	# Remove any comments from the template
	cleaned = re.sub(r'%.*\n', '', raw)
	return cleaned

TEMPLATE = load_template()

with open_relative('replacements.json', encoding = 'utf-8') as _f:
	TEX_REPLACEMENTS = json.load(_f)


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
	def __init__(self, log):
		self.log = log

	def __str__(self):
		return f'RenderingError@{id(self)}'

	def __repr__(self):
		return f'RenderingError@{id(self)}'


class LatexModule(Cog):

	def __init__(self, bot):
		self.bot = bot

	@command(aliases=['latex', 'rtex'])
	@core.settings.command_allowed('c-tex')
	async def tex(self, context, *, latex=''):
		await self.handle(context.message, latex, is_inline=False)

	@command(aliases=['wtex'])
	@core.settings.command_allowed('c-tex')
	async def texw(self, context, *, latex=''):
		await self.handle(context.message, latex, wide=True, is_inline=False)

	@command(aliases=['ptex'])
	@core.settings.command_allowed('c-tex')
	async def texp(self, context, *, latex=''):
		await self.handle(context.message, latex, noblock=True, is_inline=False)

	@Cog.listener()
	async def on_message_discarded(self, message):
		if not message.author.bot and message.content.count('$$') >= 2 and not message.content.startswith('=='):
			if is_private(message.channel) or (await self.bot.settings.resolve_message('c-tex', message) and await self.bot.settings.resolve_message('f-inline-tex', message)):
				latex = extract_inline_tex(message.clean_content)
				if latex != '':
					await self.handle(message, latex, centre=False, is_inline=True)

	async def handle(self, message, source, *, is_inline, centre=True, wide=False, noblock=False):
		if source == '':
			await message.channel.send('Type `=help tex` for information on how to use this command.')
		else:
			print(f'LaTeX - {message.author} - {source}')
			colour_back, colour_text = await self.get_colours(message.author)
			# Content replacement has to happen last in case it introduces a marker
			latex = TEMPLATE.replace('\\begin{#BLOCK}', '').replace('\\end{#BLOCK}', '') if noblock else TEMPLATE
			latex = latex.replace('#COLOUR',  colour_text) \
			             .replace('#PAPERTYPE', 'a2paper' if wide else 'a5paper') \
			             .replace('#BLOCK', 'gather*' if centre else 'flushleft') \
			             .replace('#CONTENT', process_latex(source, is_inline))
			await self.render_and_reply(message, latex, colour_back)

	async def render_and_reply(self, message, latex, colour_back):
		with MessageEditGuard(message, message.channel, self.bot) as guard:
			async with message.channel.typing():
				sent_message = None
				try:
					render_result = await generate_image_online(latex, colour_back)
				except asyncio.TimeoutError:
					sent_message = await guard.send(LATEX_TIMEOUT_MESSAGE)
				except RenderingError as e:
					err = e.log is not None and re.search(r'^!.*?^!', e.log + '\n!', re.MULTILINE + re.DOTALL)
					if err and len(err[0]) < 1000:
						m = err[0].strip("!\n")
						sent_message = await guard.send(f'Rendering failed. Check your code. You may edit your existing message.\n\n**Error Log:**\n```\n{m}\n```')
					else:
						sent_message = await guard.send('Rendering failed. Check your code. You can edit your existing message if needed.')
				else:
					sent_message = await guard.send(file=discord.File(render_result, 'latex.png'))
					await self.bot.advertise_to(message.author, message.channel, guard)
				if sent_message:
					if await self.bot.settings.resolve_message('f-tex-trashcan', message):
						with suppress(discord.errors.NotFound):
							await sent_message.add_reaction(DELETE_EMOJI)
					if await self.bot.settings.resolve_message('f-tex-delete', message):
						with suppress(discord.errors.NotFound):
							await message.delete()

	@Cog.listener()
	async def on_reaction_add(self, reaction, user):
		if not user.bot:
			if reaction.emoji == DELETE_EMOJI:
				blame = await self.bot.keystore.get_json('blame', str(reaction.message.id))
				if blame is not None and blame['id'] == user.id:
					await reaction.message.delete()

	async def get_colours(self, user):
		colour_setting = await self.bot.keystore.get('p-tex-colour', str(user.id)) or 'dark'
		if colour_setting == 'light':
			return 'ffffff', '202020'
		elif colour_setting == 'dark':
			return '36393F', 'f0f0f0'
		# Fallback in case of other weird things
		return '36393F', 'f0f0f0'


async def generate_image_online(latex, colour_back):
	OVERSAMPLING = 2
	payload = {
		'format': 'png',
		'code': latex.strip(),
		'density': 220 * OVERSAMPLING,
		'quality': 100
	}
	async with aiohttp.ClientSession() as session:
		try:
			async with session.post(LATEX_SERVER_URL, json=payload, timeout=8) as loc_req:
				loc_req.raise_for_status()
				jdata = await loc_req.json()
				if jdata['status'] == 'error':
					raise RenderingError(jdata.get('log'))
				filename = jdata['filename']
			# Now actually get the image
			async with session.get(LATEX_SERVER_URL + '/' + filename, timeout=3) as img_req:
				img_req.raise_for_status()
				fo = io.BytesIO(await img_req.read())
				image = PIL.Image.open(fo).convert('RGBA')
		except aiohttp.client_exceptions.ClientResponseError:
			raise RenderingError(None)
	if image.width <= 2 or image.height <= 2:
		raise RenderingError(None)
	border_size = 5 * OVERSAMPLING
	colour_back = imageutil.hex_to_tuple(colour_back)
	width, height = image.size
	backing = imageutil.new_monocolour((width + border_size * 2, height + border_size * 2), colour_back)
	backing.paste(image, (border_size, border_size), image)
	if OVERSAMPLING != 1:
		backing = backing.resize((backing.width // OVERSAMPLING, backing.height // OVERSAMPLING), resample = PIL.Image.BICUBIC)
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


def process_latex(latex, is_inline):
	latex = latex.replace('`', ' ').strip(' \n')
	if latex.startswith('tex') and not is_inline:
		latex = latex[3:].strip('\n')
	for key, value in TEX_REPLACEMENTS.items():
		if key in latex:
			latex = latex.replace(key, value)
	return latex


def setup(bot):
	bot.add_cog(LatexModule(bot))
