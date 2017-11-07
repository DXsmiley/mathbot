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


core.help.load_from_file('./help/latex.md')


LATEX_SERVER_URL = 'http://rtex.probablyaweb.site/api/v2'

META_TEMPLATE = r'''
\documentclass{article}

\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{mathrsfs}
\usepackage{chemfig}
\usepackage{tikz}
\usepackage{color}
\usepackage{xcolor}
\usepackage{cancel}
\usepackage[a5paper]{geometry}

\newfam\hebfam
\font\tmp=rcjhbltx at10pt \textfont\hebfam=\tmp
\font\tmp=rcjhbltx at7pt  \scriptfont\hebfam=\tmp
\font\tmp=rcjhbltx at5pt  \scriptscriptfont\hebfam=\tmp
\edef\declfam{\ifcase\hebfam 0\or1\or2\or3\or4\or5\or6\or7\or8\or9\or A\or B\or C\or D\or E\or F\fi}
\mathchardef\shin   = "0\declfam 98
\mathchardef\aleph  = "0\declfam 27
\mathchardef\beth   = "0\declfam 62
\mathchardef\gimel  = "0\declfam 67
\mathchardef\daleth = "0\declfam 64
\mathchardef\ayin   = "0\declfam 60
\mathchardef\tsadi  = "0\declfam 76
\mathchardef\qof    = "0\declfam 72
\mathchardef\lamed  = "0\declfam 6C
\mathchardef\mim    = "0\declfam 6D
\newcommand{\bbR}{\mathbb{R}}
\newcommand{\bbQ}{\mathbb{Q}}
\newcommand{\bbC}{\mathbb{C}}
\newcommand{\bbZ}{\mathbb{Z}}
\newcommand{\bbN}{\mathbb{N}}
\newcommand{\bbH}{\mathbb{H}}
\newcommand{\bbK}{\mathbb{K}}
\newcommand{\bbG}{\mathbb{G}}
\newcommand{\bbP}{\mathbb{P}}
\newcommand{\bbX}{\mathbb{X}}
\newcommand{\bbD}{\mathbb{D}}
\newcommand{\bbO}{\mathbb{O}}
\newcommand{\bigO}{\mathcal{O}}

\begin{document}

\pagenumbering{gobble}

\definecolor{my_colour}{HTML}{#COLOUR}
\color{my_colour}

\begin{#BLOCK}
#CONTENT
\end{#BLOCK}

\end{document}
'''

TEMPLATE = META_TEMPLATE.replace('#BLOCK', 'gather*')
TEMPLATE_INLINE = META_TEMPLATE.replace('#BLOCK', 'flushleft')

# Error messages

LATEX_TIMEOUT_MESSAGE = 'The renderer took too long to respond.'

PERMS_FAILURE = '''\
I don't have permission to upload images here :frowning:
The owner of this server should be able to fix this issue.
'''

TEX_REPLACEMENTS = {
	# Capital greek letters
	'Γ': r' \Gamma ',
	'Δ': r' \Delta ',
	'Θ': r' \Theta ',
	'Λ': r' \Lambda ',
	'Ξ': r' \Xi ',
	'Π': r' \Pi ',
	'Σ': r' \Sigma',
	'Υ': r' \Upsilon',
	'Φ': r' \Phi ',
	'Ψ': r' \Psi ',
	'Ω': r' \Omega',
	# Lower case greek letters
	'α': r' \alpha ',
	'β': r' \beta ',
	'γ': r' \gamma ',
	'δ': r' \delta ',
	'ε': r' \epsilon ',
	'ζ': r' \zeta ',
	'η': r' \eta ',
	'θ': r' \theta ',
	'ι': r' \iota ',
	'κ': r' \kappa ',
	'λ': r' \lambda ',
	'μ': r' \mu ',
	'ν': r' \nu ',
	'ξ': r' \xi ',
	'π': r' \pi ',
	'ρ': r' \rho ',
	'ς': r' \varsigma ',
	'σ': r' \sigma ',
	'τ': r' \tau ',
	'υ': r' \upsilon ',
	'φ': r' \phi ',
	'χ': r' \chi ',
	'ψ': r' \psi ',
	'ω': r' \omega ',
	# Cyrillic
	# Mathematical symbols
	'×': r' \times ',
	'÷': r' \div ',
	# Hebrew
	'ש': r' \shin ',
	'א': r' \alef ',
	'ב': r' \beth ',
	'ג': r' \gimel ',
	'ד': r' \daleth ',
	'ל': r' \lamed ',
	'מ': r' \mim ',
	'ם': r' \mim ',
	'ע': r' \ayin ',
	'צ': r' \tsadi ',
	'ץ': r' \tsadi ',
	'ק': r' \qof ',
	'·': r' \cdot ',
	'•': r' \cdot '
}


class RenderingError(Exception):
	pass


class LatexModule(core.module.Module):

	def __init__(self):
		# IDEA: Store this in redis
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
		if not message.author.bot and not message.content.startswith('=') and message.content.count('$$') >= 2:
			if message.channel.is_private or (await core.settings.get_setting(message, 'c-tex') and await core.settings.get_setting(message, 'f-inline-tex')):
				latex = extract_inline_tex(message.clean_content)
				if latex != '':
					await self.handle(message, latex, 'inline')

	@core.handles.on_edit()
	async def inline_edit(self, before, after):
		if not after.content.startswith('=') and after.content.count('$$') >= 2 and before.content != after.content:
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
		try:
			render_result = await generate_image_online(latex, colour_back = colour_back, colour_text = colour_text)
		except asyncio.TimeoutError:
			return await self.send_message(message.channel, LATEX_TIMEOUT_MESSAGE, blame = message.author)
		except RenderingError:
			print('Rendering Error')
			return await self.send_message(message.channel,
				'Rendering failed. Check your code. You can edit your existing message if needed.',
				blame = message.author
			)
		else:
			print('Success!')
			content = None
			if await advertising.should_advertise_to(message.author, message.channel):
				content = 'Support the bot on Patreon: <https://www.patreon.com/dxsmiley>'
			return await self.send_image(message.channel, render_result, fname = 'latex.png', blame = message.author, content = content)


async def generate_image_online(latex, colour_back = None, colour_text = '000000'):
	payload = {
		'format': 'png',
		'code': latex.strip(),
	}
	async with aiohttp.ClientSession() as session:
		async with session.post(LATEX_SERVER_URL, json = payload, timeout = 8) as loc_req:
			loc_req.raise_for_status()
			jdata = await loc_req.json()
			# print('LOG:\n', jdata.get('log'))
			# print(jdata.get('status'))
			# print(jdata.get('description'))
			if jdata['status'] == 'error':
				raise RenderingError
			filename = jdata['filename']
		# Now actually get the image
		async with session.get(LATEX_SERVER_URL + '/' + filename, timeout = 3) as img_req:
			img_req.raise_for_status()
			fo = io.BytesIO(await img_req.read())
			image = PIL.Image.open(fo).convert('RGBA')
	if colour_back is not None:
		colour_back = imageutil.hex_to_tuple(colour_back)
		back = imageutil.new_monocolour(image.size, colour_back)
		back.paste(image, (0, 0), image)
		image = imageutil.add_border(back, 4, colour_back)
	return image


async def get_colours(message):
	colour_setting = await core.settings.get_setting(message, 'p-tex-colour')
	if colour_setting == 'transparent':
		colour_text = '737f8d'
		colour_back = None
	elif colour_setting == 'light':
		colour_text = '202020'
		colour_back = 'ffffff'
	elif colour_setting == 'dark':
		colour_text = 'f0f0f0'
		colour_back = '36393E'
	return colour_back, colour_text


def extract_inline_tex(content):
	parts = iter(content.split('$$'))
	latex = ''
	try:
		while True:
			word = next(parts)
			if word != '':
				latex += '{} '.format(word.replace('#', '\#').replace('$', '\$'))
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
