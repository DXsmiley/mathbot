# Calculator module

import re

import asyncio

import safe
import core.help
import core.module
import core.handles
import core.settings
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


SCOPES = collections.defaultdict(calculator.blackbox.Terminal)


class CalculatorModule(core.module.Module):

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
			if arg.count(':') > 0:
				await self.send_message(message.channel, 'The `:` operator has been removed from the language.', blame = message.author)
			else:
				scope = SCOPES[message.channel.id]
				result, worked = await scope.execute_async(arg)
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
