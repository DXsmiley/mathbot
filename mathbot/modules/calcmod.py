# Calculator module

import re
import asyncio
import utils
import safe
import core.help
import core.util
import core.settings
import calculator
import calculator.blackbox
import collections
import traceback
import patrons
import advertising
import aiohttp
import async_timeout
import json
import time
import traceback
import typing
import discord
import abc
import functools

from discord.ext.commands import command, guild_only, has_permissions, Cog

core.help.load_from_file('./help/calculator_brief.md')
core.help.load_from_file('./help/calculator_full.md')
core.help.load_from_file('./help/calculator_history.md')
core.help.load_from_file('./help/calculator_libraries.md')
core.help.load_from_file('./help/turing.md')
core.help.load_from_file('./help/turing_functions.md')
# core.help.load_from_file('./help/turing.md')


SHORTCUT_HELP_CLARIFICATION = '''\
The `==` prefix is a shortcut for the `{prefix}calc` command.
For information on how to use the bot, type `{prefix}help`.
For information on how to use the `{prefix}calc`, command, type `{prefix}help calc`.
'''

HISTORY_DISABLED = '''\
Command history is not avaiable on this server.
'''

HISTORY_DISABLED_PRIVATE = '''\
Private command history is only avaiable to quadratic Patreon supporters: https://www.patreon.com/dxsmiley
A support teir of **quadratic** or higher is required.
'''


SCOPES = dict()

async def get_scope(place):
	if place not in SCOPES:
		SCOPES[place] = await calculator.blackbox.Terminal.new_blackbox(
			retain_cache=False,
			output_limit=1950,
			yield_rate=1,
			runtime_protection_level=2
		)
	return SCOPES[place]


LOCKS = collections.defaultdict(asyncio.Lock)


COMMAND_DELIM = '####'
EXPIRE_TIME = 60 * 60 * 24 * 10 # Things expire in 10 days


class ReplayState:
	__slots__ = ['semaphore', 'loaded']
	def __init__(self):
		self.semaphore = asyncio.Semaphore()
		self.loaded = False


ENABLE_LIBS = True
ENABLE_HISTORY = True


class CalculatorModule(Cog):

	__slots__ = ['bot', 'command_history', 'replay_state']

	def __init__(self, bot):
		self.bot = bot
		self.command_history = collections.defaultdict(lambda : '')
		self.replay_state = collections.defaultdict(ReplayState)

	@command()
	@core.settings.command_allowed('c-calc')
	async def calc(self, ctx, *, arg):
		''' Handle the standard =calc command '''
		await self.perform_calculation(arg.strip(), ctx.message, ctx.send)

	@command(name='calc-history', enabled=ENABLE_HISTORY)
	async def handle_view_history(self, ctx):
		''' Command to view the list of recently run expressions. '''
		if not await self.allow_calc_history(ctx.channel):
			await ctx.send(HISTORY_DISABLED_PRIVATE if utils.is_private(ctx.channel) else HISTORY_DISABLED)
		else:
			commands = await self.unpack_commands(ctx.channel)
			if not commands:
				await ctx.send('No persistent commands have been run in this channel.')
			else:
				commands_text = map(lambda x: x['expression'], commands)
				for i in history_grouping(commands_text):
					await ctx.send(i)

	@command(name='libs-list', enabled=ENABLE_LIBS)
	@guild_only()
	@core.settings.command_allowed('c-calc')
	@core.util.respond
	async def handle_libs_list(self, ctx):
		''' Command to list all the libraries installed in this server '''
		libs = await self.bot.keystore.get_json('calculator', 'libs', str(ctx.guild.id))
		if not libs:
			return 'This server has no calculator libraries installed.'
		embed = discord.Embed(title="Installed libraries")
		for i in libs:
			embed.add_field(name=i['name'], value=i['url'])
		return embed

	@command(name='libs-add', enabled=ENABLE_LIBS)
	@guild_only()
	@has_permissions(administrator=True)
	@core.util.respond
	async def handle_libs_add(self, ctx, *, url):
		print('Adding a library')
		''' Command to add a new library to the server '''
		if not await self.allow_calc_history(ctx.channel):
			return discord.Embed(
				title='This feature is Patron-only',
				description='This feature is currently only avaiable to bot patrons. Go to bit.ly/mathbot to become a patron.',
				colour=discord.Colour.red()

			)
		# Filter out non-libraries
		if not url.startswith('https://gist.github.com/'):
			return discord.Embed(
				title='Library load error',
				description='Parameter was not a gist url',
				colour=discord.Colour.red()
			)
		# Download 
		async with aiohttp.ClientSession() as session:
			lib_info = await download_library(session, url)
			if isinstance(lib_info, LibraryDownloadIssue):
				return discord.Embed(
					title='Library load error',
					description=str(lib_info),
					colour=discord.Colour.red(),
					url=lib_info.url
				)
		# Get list of existing libraries
		libs = await self.bot.keystore.get_json('calculator', 'libs', str(ctx.guild.id)) or []
		# Ensure that the library is not already installed
		if url in map(lambda x: x['url'], libs):
			return discord.Embed(
				title='Library load error',
				description='That library has already been added to this server.',
				colour=discord.Colour.red()
			)
		# Limit the number of libraries allow on a single server
		if len(libs) >= 10:
			return discord.Embed(
				title='Library add error',
				description='Servers cannot have more than ten libraries installed at once. If you want to complain about this poke @DXsmiley over here: https://discord.gg/JbJbRZS',
				colour=discord.Colour.red()
			)
		# Add the new library to the list and store it again
		libs.append({
			'url': url,
			'name': lib_info.name
		})
		await self.bot.keystore.set_json('calculator', 'libs', str(ctx.guild.id), libs)
		return discord.Embed(
			title='Added library',
			description=lib_info.name,
			url=lib_info.url,
			footer='Run `=calc-reload` to load the library.'
		)

	@command(name='libs-remove', enabled=ENABLE_LIBS)
	@guild_only()
	@has_permissions(administrator=True)
	@core.util.respond
	async def handle_libs_remove(self, message, url):
		''' Command to remove a library from the list '''
		libs = await self.bot.keystore.get_json('calculator', 'libs', str(message.guild.id)) or []
		if not url in map(lambda x: x['url'], libs):
			return discord.Embed(
				title='Failed to remove library',
				colour=discord.Colour.red()
			)
		libs = list(filter(lambda x: x['url'] != url, libs))
		await self.bot.keystore.set_json('calculator', 'libs', str(message.guild.id), libs)
		return discord.Embed(
			title='Removed library',
			footer='Run `=calc-reload` to properly unload it.',
			colour=discord.Colour.blue()
		)

	@command(name='calc-reload')
	@core.settings.command_allowed('c-calc')
	async def handle_calc_reload(self, ctx):
		channel = ctx.channel.id
		async with LOCKS[channel]:
			if channel in SCOPES:
				del SCOPES[channel]
			if channel in self.replay_state:
				del self.replay_state[channel]
		await ctx.send('Calculator state has been flushed from this channel.')

	@Cog.listener()
	async def on_message_discarded(self, message):
		''' Trigger the calculator when the message is prefixed by "==" '''
		async def send(*args, **kwargs):
			msg = await message.channel.send(*args, **kwargs)
			await core.blame.set_blame(self.bot.keystore, msg, message.author)
			return msg
		arg = message.content
		if len(arg) > 2 and \
		   arg.startswith('==') and \
		   arg[2] not in '=<>+*/!@#$%^&' and \
		   'results from bdsmtest.org' not in arg.lower() and \
		   await self.bot.settings.resolve_message('f-calc-shortcut', message):
			if not await self.bot.settings.resolve_message('c-calc', message):
				raise core.settings.DisabledCommandByServerOwner
			await self.perform_calculation(arg.strip()[2:], message, send)

	# Perform a calculation and spits out a result!
	async def perform_calculation(self, arg, message, send):
		async with LOCKS[message.channel.id]:
			await self.ensure_loaded(message.channel, message.author)
			# Yeah this is kinda not great...
			arg = arg.strip('` \n\t')
			if arg == '':
				# If no equation was given, spit out the help.
				if not message.content.startswith('=='):
					await send('Type `=help calc` for information on how to use this command.')
			elif arg == 'help':
				prefix = await self.bot.settings.get_server_prefix(message)
				await send(SHORTCUT_HELP_CLARIFICATION.format(prefix=prefix))
			else:
				safe.sprint('Doing calculation:', arg)
				scope = await get_scope(message.channel.id)
				result, worked, details = await scope.execute_async(arg)
				if result.count('\n') > 7:
					lines = result.split('\n')
					num_removed_lines = len(lines) - 8
					selected = '\n'.join(lines[:8]).replace('`', '`\N{zero width non-joiner}')
					result = '```\n{}\n```\n{} lines were removed.'.format(selected, num_removed_lines)
				elif result.count('\n') > 0:
					result = '```\n{}\n```'.format(result.replace('`', '`\N{zero width non-joiner}'))
				else:
					for special_char in ('\\', '*', '_', '~~', '`'):
						result = result.replace(special_char, '\\' + special_char)
				result = result.replace('@', '@\N{zero width non-joiner}')
				if result == '':
					await message.add_reaction('👍')
				else:
					if result == '':
						result = ':thumbsup:'
					elif len(result) > 2000:
						result = 'Result was too large to display.'
					await send(result)
				if worked:
					await self.bot.advertise_to(message.author, message.channel, message.channel)
					if expression_has_side_effect(arg):
						await self.add_command_to_history(message.channel, arg)
				safe.sprint('Finished calculation:', arg)

	async def ensure_loaded(self, channel, blame):
		# If command were previously run in this channel, re-run them
		# in order to re-load any functions that were defined
		if await self.allow_calc_history(channel):
			# Ensure that only one coroutine is allowed to execute the code
			# in this block at once.
			async with self.replay_state[channel.id].semaphore:
				if not self.replay_state[channel.id].loaded:
					if ENABLE_LIBS and not utils.is_private(channel):
						print('Loading libraries for channel', channel)
						await self.run_libraries(channel, channel.guild)
					if ENABLE_HISTORY:
						print('Replaying calculator commands for', channel)
						await self.restore_history(channel, blame)
					self.replay_state[channel.id].loaded = True

	async def restore_history(self, channel, blame):
		commands_unpacked = await self.unpack_commands(channel)
		if not commands_unpacked:
			print('No commands')
		else:
			was_error, commands_to_keep = await self.rerun_commands(channel, commands_unpacked)
			# Store the list of commands that worked back into storage for use next time
			to_store = json.dumps(commands_to_keep)
			await self.bot.keystore.set('calculator', 'history', str(channel.id), to_store, expire = EXPIRE_TIME)
			if was_error:
				await channel.send(embed=discord.Embed(
					title='Some errors occurred during catchup.',
					description='Calculator state has been partially restored. Run `=calc-history` for a list of commands that have been retained.',
					colour=discord.Colour.red()
				))

	async def unpack_commands(self, channel):
		commands = await self.bot.keystore.get('calculator', 'history', str(channel.id))
		if commands is None:
			print('No commands to unpack')
			return []
		try:
			commands_unpacked = json.loads(commands)
			return commands_unpacked
		except json.JSONDecodeError:
			print('JSON Decode failed when unpacking commands')
			return []

	async def run_libraries(self, channel, guild):
		scope = await get_scope(channel.id)
		libs = await self.bot.keystore.get_json('calculator', 'libs', str(guild.id))
		downloaded = await download_libraries(i['url'] for i in (libs or []))
		success = all(map(lambda r: isinstance(r, LibraryDownloadSuccess), downloaded))
		if not downloaded:
			print('No libraries')
		elif not success:
			for i in downloaded:
				if isinstance(i, LibraryDownloadIssue):
					# TODO: Blame message
					await channel.send(
						embed = discord.Embed(
							title='Library load error',
							description=str(i),
							colour=discord.Colour.red(),
							url=i.url
						)
					)
					await asyncio.sleep(1.05)
		else:
			errors = []
			for lib in downloaded:
				print(f'library | {lib.url}')
				result, worked, details = await scope.execute_async(lib.code)
				# print(result, worked)
				if not worked:
					errors.append(f'**Error in {lib.url}**\n```{result}```')
			# TODO: Blame message
			await channel.send(
				embed = discord.Embed(
					title='Errors occurred while running the libraries.',
					description='Use `=calc-reload` to try again.\n' + '\n\n\n'.join(errors)[:2000],
					colour=discord.Colour.red()
				)
			)

	async def rerun_commands(self, channel, commands):
		scope = await get_scope(channel.id)
		commands_to_keep = []
		was_error = False
		time_cutoff = int(time.time()) - EXPIRE_TIME
		for command in commands:
			ctime = command['time']
			expression = command['expression']
			# print(f'>>> {expression}')
			if ctime > time_cutoff:
				result, worked, details = await scope.execute_async(expression)
				was_error = was_error or not worked
				if worked:
					commands_to_keep.append(command)
			else:
				print('    (dropped due to age)')
		return was_error, commands_to_keep

	async def add_command_to_history(self, channel, new_command):
		if await self.allow_calc_history(channel):
			history = await self.unpack_commands(channel)
			history.append({
				'time': int(time.time()),
				'expression': new_command
			})
			to_store = json.dumps(history)
			await self.bot.keystore.set('calculator', 'history', str(channel.id), to_store, expire = EXPIRE_TIME)

	async def allow_calc_history(self, channel):
		# if not self.bot.parameters.get('calculator.persistent'):
		# 	return False
		if self.bot.parameters.get('release') == 'development':
			return True
		if not ENABLE_HISTORY:
			return False
		if utils.is_private(channel):
			return (await self.bot.patron_tier(channel.recipient.id)) >= patrons.TIER_CONSTANT
		else:
			return (await self.bot.patron_tier(channel.guild.owner_id)) >= patrons.TIER_CONSTANT


def expression_has_side_effect(expr):
	# This is a hack. The only way a command is actually 'important' is
	# if it assignes a variable. Variables are assigned through the = or -> operators.
	# This can safely return a false positive, but should never return a false negitive.
	expr.replace('==', '')
	expr.replace('>=', '')
	expr.replace('<=', '')
	return any(map(expr.__contains__, ['=', '->', '~>', 'unload?']))


def history_grouping(commands):
	current = []
	current_size = 0
	for i in commands:
		i_size = len(i) + 12 # Length of string: '```\n{}\n```\n'
		if i_size + current_size > 1800:
			yield '```\n{}\n```'.format(''.join(current))
			current = []
			current_size = 0
		current.append(i + '\n')
		current_size += i_size
	yield '```\n{}\n```'.format(''.join(current))


class LibraryDownloadResult(abc.ABC):

	@property
	@abc.abstractmethod
	def error_string(self) -> str:
		...

	def __str__(self) -> str:
		return f'```\n{self.error_string}\n```'


class LibraryDownloadSuccess(LibraryDownloadResult):

	def __init__(self, url: str, name: str, docs: str, code: str) -> None:
		self.url  = url
		self.name = name
		self.docs = docs
		self.code = code

	@property
	def error_string(self) -> str:
		return 'Successful'


class LibraryDownloadIssue(LibraryDownloadResult):

	def __init__(self, url: str, reason: str) -> None:
		self.url = url
		self.reason = reason

	@property
	def error_string(self) -> str:
		return self.reason


class LibraryDownloadError(Exception):

	def __init__(self, reason):
		self.reason = reason


async def download_libraries(urls: [str]) -> [LibraryDownloadResult]:
	async with aiohttp.ClientSession() as session:
		results = await asyncio.gather(*[
			download_library(session, i) for i in urls
		])
	return results


async def download_library(session: aiohttp.ClientSession, url: str) -> LibraryDownloadResult:
	try:
		async with async_timeout.timeout(10):
			identifier = url.rsplit('/', 1)[1]
			return await download_gist(session, url, identifier)
	except LibraryDownloadError as e:
		return LibraryDownloadIssue(url, e.reason)
	except Exception as e:
		# TODO: Make these more user friendly.
		return LibraryDownloadIssue(url, traceback.format_exc())


async def download_gist(session: aiohttp.ClientSession, original_url: str, gist_id: str) -> LibraryDownloadResult:
	url = f'https://api.github.com/gists/{gist_id}'
	url_code = None
	url_docs = None
	author = None
	author_av = None
	async with session.get(url) as response:

		if response.status == '404':
			raise LibraryDownloadError('Library not found (server produced 404)')

		response.raise_for_status()

		blob = await response.json()
		author = blob['owner']['login']
		author_av = blob['owner']['avatar_url']
		description = blob['description']

		for filename, metadata in blob['files'].items():
			fn = filename.lower()
			if match_filename(filename, ('readme', 'help'), ('md', 'txt', 'rst')):
				if url_docs is not None:
					raise LibraryDownloadError('Found multiple documentation files. Requires exactly 1.')
				url_docs = metadata['raw_url']
			elif match_filename(filename, ('source',), ('',)):
				if url_code is not None:
					raise LibraryDownloadError('Found multiple code files. Requires exactly 1.')
				url_code = metadata['raw_url']

	if url_code is None:
		raise LibraryDownloadError('Gist had no code files')

	code = await download_text(session, url_code)
	docs = (await download_text(session, url_docs)) if url_docs is not None else ''

	return LibraryDownloadSuccess(
		original_url,
		description,
		docs,
		code
	)


def match_filename(specimen, allowed_names, allowed_exts):
	specimen = specimen.lower()
	assert all(map(lambda s: s == '' or s.islower(), allowed_names))
	assert all(map(lambda s: s == '' or s.islower(), allowed_exts))
	if specimen.count('.') == 0:
		return specimen in allowed_names and '' in allowed_exts
	elif specimen.count('.') == 1:
		name, ext = specimen.split('.')
		return name in allowed_names and ext in allowed_exts
	return False


async def download_text(session: aiohttp.ClientSession, url: str) -> str:
	async with session.get(url) as response:
		data = await response.text()
		if len(data) > 1000 * 32: # 32 KB
			raise LibraryDownloadError('Downloaded file is too large (limit of 32,000 bytes)')
		return data


def setup(bot):
	bot.add_cog(CalculatorModule(bot))
