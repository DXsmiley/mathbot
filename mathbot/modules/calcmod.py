# Calculator module

import re

import asyncio

import safe
import core.help
import core.module
import core.handles
import core.settings
import core.keystore
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

core.help.load_from_file('./help/calculator.md')
core.help.load_from_file('./help/calculator_sort.md')
core.help.load_from_file('./help/calculator_history.md')
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


class CalculatorModule(core.module.Module):

	def __init__(self):
		self.command_history = collections.defaultdict(lambda : '')
		self.replay_state = collections.defaultdict(ReplayState)

	@core.handles.command('calc', '*', perm_setting='c-calc')
	async def handle_calc(self, message, arg):
		''' Handle the standard =calc command '''
		await self.perform_calculation(arg.strip(), message)

	@core.handles.command('calc-history', '', perm_setting='c-calc')
	async def handle_view_history(self, message):
		''' Command to view the list of recently run expressions. '''
		if not self.allow_calc_history(message.channel):
			return HISTORY_DISABLED_PRIVATE if message.channel.is_private else HISTORY_DISABLED
		commands = await self.unpack_commands(message.channel)
		if not commands:
			return 'No persistent commands have been run in this channel.'
		commands_text = map(lambda x: x['expression'], commands)
		for i in history_grouping(commands_text):
			await self.send_message(message, i)

	@core.handles.command('libs-list', '', perm_setting='c-calc', no_dm=True)
	async def handle_libs_list(self, message):
		libs = await core.keystore.get_json('calculator', 'libs', message.server.id)
		if not libs:
			return 'This server has no calculator libraries installed.'
		embed = discord.Embed(title="Installed libraries")
		for i in libs:
			embed.add_field(name=i['name'], value=i['url'])
		return embed
		# listing = '\n'.join(map(lambda x: ' - ' + x, libs))
		# ll = len(libs)
		# return f'This server has **{ll}** librar{"y" if ll == 1 else "ies"} installed:\n{listing}'

	@core.handles.command('libs-add', 'string', perm_setting='c-calc', no_dm=True, discord_perms='manage_server')
	async def handle_libs_add(self, message, url):
		if not url.startswith('https://gist.github.com/'):
			return discord.Embed(
				title='Library load error',
				description='Parameter was not a gist url',
				colour = discord.Colour.red()
			)
		# Download 
		async with aiohttp.ClientSession() as session:
			lib_info = await download_library(session, url)
			if isinstance(lib_info, LibraryDownloadIssue):
				return discord.Embed(
					title='Library load error',
					description=str(lib_info),
					colour=discord.Colour.red(),
					url=lib_info.url()
				)
		libs = await core.keystore.get_json('calculator', 'libs', message.server.id) or []
		if url in map(lambda x: x['url'], libs):
			return discord.Embed(
				title='Library load error',
				description='That library has already been added to this server.',
				colour=discord.Colour.red()
			)
		libs.append({
			'url': url,
			'name': lib_info.name
		})
		await core.keystore.set_json('calculator', 'libs', message.server.id, libs)
		return discord.Embed(
			title='Added library',
			description=lib_info.name,
			url=lib_info.url,
			footer='Run `=calc-reload` to load the library.'
		)
		# return 'Added library. Run `{prefix}calc-reload` to load it.'

	@core.handles.command('libs-remove', 'string', perm_setting='c-calc', no_dm=True, discord_perms='manage_server')
	async def handle_libs_remove(self, message, url):
		libs = await core.keystore.get_json('calculator', 'libs', message.server.id) or []
		if not url in map(lambda x: x['url'], libs):
			return 'Library URL not found.'
		libs = list(filter(lambda x: x['url'] != url, libs))
		await core.keystore.set_json('calculator', 'libs', message.server.id, libs)
		return 'Removed library. Run `{prefix}calc-reload` to unload it.'

	@core.handles.command('calc-reload calc-flush', '', perm_setting='c-calc', no_dm=True, discord_perms='manage_server')
	async def handle_calc_reload(self, message):
		with (await LOCKS[message.channel.id]):
			if message.channel.id in SCOPES:
				del SCOPES[message.channel.id]
			if message.channel.id in self.replay_state:
				del self.replay_state[message.channel.id]
		return 'Calculator state has been flushed from this channel.'

	# Trigger the calculator when the message is prefixed by "=="
	@core.handles.on_message()
	async def handle_raw_message(self, message):
		arg = message.content
		if len(arg) > 2 and arg.startswith('==') and arg[2] not in '=<>+*/!@#$%^&':
			if await core.settings.get_setting(message, 'f-calc-shortcut'):
				return core.handles.Redirect('calc', arg[2:])

	# Perform a calculation and spits out a result!
	async def perform_calculation(self, arg, message):
		with (await LOCKS[message.channel.id]):
			await self.replay_commands(message.channel, message.author)
			# Yeah this is kinda not great...
			arg = arg.strip('` \n\t')
			if arg == '':
				# If no equation was given, spit out the help.
				if not message.content.startswith('=='):
					await self.send_message(message, 'Type `=help calc` for information on how to use this command.')
			elif arg == 'help':
				prefix = await core.settings.get_channel_prefix(message.channel)
				await self.send_message(message, SHORTCUT_HELP_CLARIFICATION.format(prefix = prefix))
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
				if result == '' and (message.channel.is_private or message.channel.permissions_for(message.server.me).add_reactions):
					await self.client.add_reaction(message, '👍')
				else:
					if result == '':
						result = ':thumbsup:'
					elif len(result) > 2000:
						result = 'Result was too large to display.'
					elif worked and len(result) < 1000:
						if await advertising.should_advertise_to(message.author, message.channel):
							result += '\nSupport the bot on Patreon: <https://www.patreon.com/dxsmiley>'
					await self.send_message(message, result)
				if worked and expression_has_side_effect(arg):
					await self.add_command_to_history(message.channel, arg)

	async def replay_commands(self, channel, blame):
		# If command were previously run in this channel, re-run them
		# in order to re-load any functions that were defined
		if self.allow_calc_history(channel):
			# Ensure that only one coroutine is allowed to execute the code
			# in this block at once.
			async with self.replay_state[channel.id].semaphore:
				if not self.replay_state[channel.id].loaded:
					print('Loading libraries for channel', channel)
					load_msg = await self.run_libraries(channel, channel.server)
					if load_msg:
						await self.send_message(channel, load_msg, blame=blame)
					print('Replaying calculator commands for', channel)
					commands_unpacked = await self.unpack_commands(channel)
					if not commands_unpacked:
						print('No commands')
					else:
						await self.send_message(channel, 'Re-running command history...', blame = blame)
						was_error, commands_to_keep = await self.rerun_commands(channel, commands_unpacked)
						if was_error:
							await self.send_message(channel, 'Catchup complete. Some errors occurred.', blame = blame)
						else:
							await self.send_message(channel, 'Catchup complete.', blame = blame)
						# Store the list of commands that worked back into storage for use next time
						to_store = json.dumps(commands_to_keep)
						await core.keystore.set('calculator', 'history', channel.id, to_store, expire = EXPIRE_TIME)
					self.replay_state[channel.id].loaded = True

	async def unpack_commands(self, channel):
		commands = await core.keystore.get('calculator', 'history', channel.id)
		if commands is None:
			print('No commands to unpack')
			return []
		try:
			commands_unpacked = json.loads(commands)
			return commands_unpacked
		except json.JSONDecodeError:
			print('JSON Decode failed when unpacking commands')
			return []

	async def run_libraries(self, channel, server):
		scope = await get_scope(channel.id)
		libs = await core.keystore.get_json('calculator', 'libs', server.id)
		downloaded = await download_libraries(i['url'] for i in (libs or []))
		success = all(map(lambda r: isinstance(r, LibraryDownloadSuccess), downloaded))
		if not downloaded:
			print('No libraries')
		elif not success:
			for i in downloaded:
				if isinstance(i, LibraryDownloadIssue):
					await self.send_message(channel,
						discord.Embed(
							title='Library load error',
							description=str(i),
							colour=discord.Colour.red(),
							url=lib_info.url()
						)
					)
					await asyncio.sleep(1.05)
			return discord.Embed(description='Since there were errors, the calculator state has remained unchanged.')
		else:
			errors = []
			for lib in downloaded:
				print(f'library | {lib.url}')
				result, worked, details = await scope.execute_async(lib.code)
				# print(result, worked)
				if not worked:
					errors.append(f'**Error in library:** {lib.url}\n\n```{result}```')
			return '\n\n\n'.join(errors)[:2000]

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
		if self.allow_calc_history(channel):
			history = await self.unpack_commands(channel)
			history.append({
				'time': int(time.time()),
				'expression': new_command
			})
			to_store = json.dumps(history)
			await core.keystore.set('calculator', 'history', channel.id, to_store, expire = EXPIRE_TIME)

	def allow_calc_history(self, channel):
		if channel.is_private:
			return patrons.tier(channel.user.id) >= patrons.TIER_QUADRATIC
		else:
			return patrons.tier(channel.server.owner.id) >= patrons.TIER_QUADRATIC


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


class LibraryDownloadResult:

	def __init__(self) -> None:
		raise NotImplementedError

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


async def download_gist(session: aiohttp.ClientSession, original_url:str, gist_id: str) -> LibraryDownloadResult:
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
			if filename.lower() in ['readme.md', 'readme.txt']:
				if url_docs is not None:
					raise LibraryDownloadError('Found multiple documentation files. Requires exactly 1.')
				url_docs = metadata['raw_url']
			else:
				if url_code is not None:
					raise LibraryDownloadError('Found multiple code files. Requires exactly 1.')
				url_code = metadata['raw_url']

	if url_code is None:
		raise LibraryDownloadError('Gist had no code files')

	code = await download_text(session, url_code)
	docs = (await download_text(session, url_docs)) if url_docs is not None else ''

	return LibraryDownloadSuccess(
		url,
		description,
		docs,
		code
	)


async def download_text(session: aiohttp.ClientSession, url: str) -> LibraryDownloadResult:
	async with session.get(url) as response:
		data = await response.text()
		if len(data) > 1000 * 32: # 32 KB
			raise LibraryDownloadError('Downloaded file is too large (limit of 32,000 bytes)')
		return data