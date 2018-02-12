# Calculator module

import re

import asyncio

import safe
import core.help
import core.module
import core.handles
import core.settings
import calculator
# import calculator.texify
import calculator.attempt6
import collections
import traceback
import patrons
import advertising
import aiohttp

core.help.load_from_file('./help/calculator.md')
core.help.load_from_file('./help/calculator_sort.md')
core.help.load_from_file('./help/turing.md')


def wrap_if_plus(s):
	if '+' in s or '-' in s:
		return '(' + s + ')'
	return s


def format_result(x):
	if x is None:
		return 'null'
	if isinstance(x, complex):
		return '{}+{}**i**'.format(
			wrap_if_plus(format_result(x.real)),
			wrap_if_plus(format_result(x.imag))
		)
	if isinstance(x, int):
		return str(x)
	if isinstance(x, float):
		if abs(x) < 1e-22:
			return '0'
		if abs(x) > 1e10 or abs(x) < 1e-6:
			s = '{:.8e}'.format(x)
			return re.sub(r'\.?0*e', 'e', s)
		return '{:.8f}'.format(x).rstrip('0').rstrip('.')
	return '"{}"'.format(str(x))


SCOPES = collections.defaultdict(calculator.new_scope)


async def process_command(arg, scope, limits):
	arg = arg.replace('`', ' ')
	values = []
	reps = 1
	warnings = []
	if ':' in arg:
		s = arg.split(':')
		w, reps = await calculator.calculate_async(s[1], scope = scope, limits = limits)
		warnings += w
		reps = min(50, int(reps))
		arg = s[0]
	for i in range(reps):
		w, result = await calculator.calculate_async(arg, scope = scope, limits = limits)
		warnings += w
		values.append(result)
	return list(set(warnings)), values


PARSE_ERROR_TEMPLATE = '''\
Failed to parse equation: {message} at position {position}\n
```
{string}
{carat}
```
'''

SHORTCUT_HELP_CLARIFICATION = '''\
The `==` prefix is a shortcut for the `{prefix}calc` command.
For information on how to use the bot, type `{prefix}help`.
For information on how to use the `{prefix}calc`, command, type `{prefix}help calc`.
'''


def format_parse_error(message, string, position):
	DISTANCE = 30
	length = len(string)
	string = string.replace('\n', ' ').replace('\t', ' ')
	string = string[
		max(0, position - DISTANCE):
		min(length, position + DISTANCE)
	]
	if position - DISTANCE > 0:
		string = '...' + string
	if position + DISTANCE < length:
		string += '...'
	padding = min(DISTANCE, position)
	return PARSE_ERROR_TEMPLATE.format(
		message = message,
		position = position,
		string = string,
		carat = padding * ' ' + '^'
	)


class CalculatorModule(core.module.Module):

	def __init__(self, is_dev):
		core.module.Module.__init__(self)
		self.is_dev = is_dev

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
		if arg == '':
			# If no equation was given, spit out the help.
			if not message.content.startswith('=='):
				await self.send_message(message.channel, 'Type `=help calc` for information on how to use this command.', blame = message.author)
		elif arg == 'help':
			prefix = await core.settings.get_channel_prefix(message.channel)
			await self.send_message(message.channel, SHORTCUT_HELP_CLARIFICATION.format(prefix = prefix))
		else:
			safe.sprint('Doing calculation:', arg)
			if arg.count(':') > 1:
				await self.send_message(message.channel, 'There are too many `:` characters in that equation.', blame = message.author)
			else:
				error = None
				scope = SCOPES[message.channel.id]
				# Determine the stack size and time limit depending on whether
				# the person has the sufficient patreon reward tier
				limits = {'stack_size': 200, 'warnings': True}
				time_limit = 10
				if patrons.tier(message.author.id) >= patrons.TIER_QUADRATIC:
					limits['stack_size'] = 500
					time_limit = 20
				# Actually run the command, and handles the errors
				try:
					future = process_command(arg, scope, limits)
					warnings, values = await asyncio.wait_for(future, timeout = time_limit)
				except asyncio.TimeoutError:
					result = 'Calculation took too long'
				except calculator.EvaluationError as e:
					# traceback.print_exc()
					result = 'Error: ' + str(e)
					if len(result) > 2000:
						result = 'An error occurred, but it was too large to display.'
				except calculator.attempt6.ImbalancedBraces as e:
					result = 'Invalid syntax: Imbalanced braces'
				except calculator.attempt6.TokenizationFailed as e:
					result = format_parse_error('Invalid token', arg, e.position)
				except calculator.attempt6.ParseFailed as e:
					result = format_parse_error('Invalid syntax', arg, e.position)
				else:
					if should_sort:
						values.sort()
					if len(values) == 0:
						result = 'There were no results :thinking:'
					else:
						result = '\n'.join(warnings + ['']) + ' '.join(map(format_result, values))
					if len(result) > 2000:
						result = 'Result was too big :('
					if len(result) < 1000 and await advertising.should_advertise_to(message.author, message.channel):
						result += '\nSupport the bot on Patreon: <https://www.patreon.com/dxsmiley>'
				safe.sprint(result)
				await self.send_message(message.channel, result, blame = message.author)
