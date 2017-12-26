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

core.help.load_from_file('./help/calculator.md')
core.help.load_from_file('./help/calculator_sort.md')
core.help.load_from_file('./help/turing.md')


SHORTCUT_HELP_CLARIFICATION = '''\
The `==` prefix is a shortcut for the `{prefix}calc` command.
For information on how to use the bot, type `{prefix}help`.
For information on how to use the `{prefix}calc`, command, type `{prefix}help calc`.
'''


SCOPES = collections.defaultdict(lambda :
	calculator.blackbox.Terminal(retain_cache = False, output_limit = 1950)
)


COMMAND_DELIM = '####'
EXPIRE_TIME = 60 * 60 * 24 * 10 # Things expire in 10 days


class CalculatorModule(core.module.Module):

	def __init__(self):
		self.command_history = collections.defaultdict(lambda : '')
		self.replay_state = collections.defaultdict(
			lambda : {
				'semaphore': asyncio.Semaphore(),
				'loaded': False
			}
		)

	@core.handles.command('calc', '*', perm_setting = 'c-calc')
	async def handle_calc(self, message, arg):
		await self.perform_calculation(arg.strip(), message)

	@core.handles.command('sort csort', '*', perm_setting = 'c-calc')
	async def hande_calc_sorted(self, message, arg):
		await self.perform_calculation(arg.strip(), message, should_sort = True)

	# Trigger the calculator when the message is prefixed by "=="
	@core.handles.on_message()
	async def handle_raw_message(self, message):
		arg = message.content
		if len(arg) > 2 and arg.startswith('==') and arg[2] not in '=<>+*/!@#$%^&':
			if await core.settings.get_setting(message, 'f-calc-shortcut'):
				return core.handles.Redirect('calc', arg[2:])

	# Perform a calculation and spits out a result!
	async def perform_calculation(self, arg, message, should_sort = False):
		await self.replay_commands(message.channel, message.author)
		arg = arg.replace('`', ' ')
		if arg == '':
			# If no equation was given, spit out the help.
			if not message.content.startswith('=='):
				await self.send_message(message.channel, 'Type `=help calc` for information on how to use this command.', blame = message.author)
		elif arg == 'help':
			prefix = await core.settings.get_channel_prefix(message.channel)
			await self.send_message(message.channel, SHORTCUT_HELP_CLARIFICATION.format(prefix = prefix))
		else:
			safe.sprint('Doing calculation:', arg)
			scope = SCOPES[message.channel.id]
			result, worked, details = await scope.execute_async(arg)
			if result.count('\n') > 0:
				result = '```\n{}\n```'.format(result)
			if result == '':
				result = ':thumbsup:'
			elif len(result) > 2000:
				result = 'Result was too large to display.'
			elif worked and len(result) < 1000:
				if await advertising.should_advertise_to(message.author, message.channel):
					result += '\nSupport the bot on Patreon: <https://www.patreon.com/dxsmiley>'
			await self.send_message(message.channel, result, blame = message.author)
			if worked:
				# This is a hack. The only way a command is actually 'important' is
				# if it assignes a variable. Variables are assigned through the = or -> operators.
				if '=' in arg or '->' in arg:
					await self.add_command_to_history(message.channel, arg)

	async def replay_commands(self, channel, blame):
		if self.allow_calc_history(channel):
			async with self.replay_state[channel.id]['semaphore']:
				if self.replay_state[channel.id]['loaded'] == False:
					print('Replaying calculator commands for', channel)
					self.replay_state[channel.id]['loaded'] = True
					commands = await core.keystore.get('calculator', 'history', channel.id)
					if commands is None:
						print('There were none')
					else:
						await self.send_message(channel, 'Re-running command history...', blame = blame)
						commands = commands.split(COMMAND_DELIM)
						new_commands = []
						was_error = False
						print('There are', len(commands), 'to run')
						for c in commands:
							print('>>>', c)
							scope = SCOPES[channel.id]
							result, worked, details = await scope.execute_async(c)
							if worked:
								new_commands.append(c)
							else:
								was_error = True
						if was_error:
							await self.send_message(channel, 'Catchup complete. Some errors occurred.', blame = blame)
						else:
							await self.send_message(channel, 'Catchup complete.', blame = blame)
						joined = COMMAND_DELIM.join(new_commands)
						await core.keystore.set('calculator', 'history', channel.id, joined, expire = EXPIRE_TIME)

	async def add_command_to_history(self, channel, new_command):
		if self.allow_calc_history(channel):
			commands = await core.keystore.get('calculator', 'history', channel.id)
			if commands == None:
				commands = new_command
			else:
				commands += COMMAND_DELIM + new_command
			await core.keystore.set('calculator', 'history', channel.id, commands, expire = EXPIRE_TIME)

	def allow_calc_history(self, channel):
		if channel.is_private:
			return patrons.tier(channel.user.id) >= patrons.TIER_QUADRATIC
		else:
			return patrons.tier(channel.server.owner.id) >= patrons.TIER_QUADRATIC

