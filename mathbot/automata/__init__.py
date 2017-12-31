#
# Automata is a small library designed to help with the
# creation of bots to test other bots. This is currently
# part of the MathBot project but if it gains enough
# traction I might fork it into its own repository
#
#
# Interfacing with the bot through discord:
#
# ::stats
#     Gives details about which tests have been
#     run and what the results were
#
# ::run test_name
#     Run a particular test
#
# ::run all
#     Run all tests
#
# ::run unrun
#     Run all tests that have not yet been run
#


import discord
import traceback
import asyncio
import re


HELP_TEXT = '''\
**::help** - Show this help
**::run** all - Run all tests
**::run** unrun - Run all tests that have not been run
**::run** *name* - Run a specific test
'''


SPECIAL_TEST_NAMES = {'all', 'unrun'}


class TestRequirementFailure(Exception): pass

class NoResponseError(TestRequirementFailure): pass

class UnexpectedResponseError(TestRequirementFailure): pass

class ErrordResponseError(TestRequirementFailure): pass

class UnexpectedSuccessError(TestRequirementFailure): pass

class HumanResponseTimeout(TestRequirementFailure): pass

class HumanResponseFailure(TestRequirementFailure): pass

class ResponseDidntMatch(TestRequirementFailure): pass


class Test:

	''' Holds data about a specific test '''

	def __init__(self, name, func, needs_human = False):
		assert(name not in SPECIAL_TEST_NAMES)
		self.name = name # The name of the test
		self.func = func # The function to run when running the test
		self.last_run = 0 # When the test was last run
		self.result = None # The result of the test (True or False) or None if it was not run
		self.needs_human = needs_human # Whether the test requires human interation


class Interface:

	''' The interface that the test functions should use to interface with discord.
		Test functions should not access the discord.py client directly.
	'''

	def __init__(self, client, channel, target):
		self.client = client # The discord.py client object
		self.channel = channel # The channel the test is running in
		self.target = target # The bot which we are testing

	async def send_message(self, content):
		''' Send a message to the testing channel. '''
		return await self.client.send_message(self.channel, content)

	async def edit_message(self, message, new_content):
		''' Modified a message. Doesn't actually care what this message is. '''
		return await self.client.edit_message(message, new_content)

	async def wait_for_failure(self):
		''' Wait for the bot to send a message that indicated that something went wrong.
			I'm not even sure why I implemented it.
		'''
		result = await self.client.wait_for_message(timeout = 20, channel = self.channel, author = self.target)
		if result is None:
			raise NoResponseError
		try:
			self.check_failure_condition(result)
		except ErrordResponseError:
			return result
		else:
			raise UnexpectedSuccessError
		return result


	async def wait_for_message(self):
		''' Waits for the bot the send a message.
			If the bot takes longer than 20 seconds, the test fails.
		'''
		result = await self.client.wait_for_message(timeout = 20, channel = self.channel, author = self.target)
		if result is None:
			raise NoResponseError
		self.check_failure_condition(result)
		return result

	async def wait_for_reply(self, content):
		''' Sends a message and returns the next message that the targeted bot sends. '''
		await self.send_message(content)
		return await self.wait_for_message()

	async def assert_message_equals(self, matches):
		''' Waits for the next message.
			If the message does not match a string exactly, fail the test.
		'''
		response = await self.wait_for_message()
		if response.content != matches:
			raise ResponseDidntMatch
		return response

	async def assert_message_contains(self, substring):
		''' Waits for the next message.
			If the message does not contain the given substring, fail the test.
		'''
		response = await self.wait_for_message()
		if substring not in response.content:
			raise ResponseDidntMatch
		return response

	async def assert_message_matches(self, regex):
		''' Waits for the next message.
			If the message does not match a regex, fail the test.
		'''
		response = await self.wait_for_message()
		if not re.match(regex, response.content):
			raise ResponseDidntMatch
		return response

	async def assert_reply_equals(self, contents, matches):
		''' Send a message and wait for a response.
			If the response does not match a string exactly, fail the test.
		'''
		await self.send_message(contents)
		response = await self.wait_for_message()
		if response.content != matches:
			raise ResponseDidntMatch
		return response

	async def assert_reply_contains(self, contents, substring):
		''' Send a message and wait for a response.
			If the response does not contain the given substring, fail the test.
		'''
		await self.send_message(contents)
		response = await self.wait_for_message()
		if substring not in response.content:
			raise ResponseDidntMatch
		return response

	async def assert_reply_matches(self, contents, regex):
		''' Send a message and wait for a response.
			If the response does not match a regex, fail the test.
		'''
		await self.send_message(contents)
		response = await self.wait_for_message()
		if not re.match(regex, response.content):
			raise ResponseDidntMatch
		return response

	async def ensure_silence(self):
		''' Ensures that the bot does not post any messages for some number of seconds. '''
		result = await self.client.wait_for_message(timeout = 20, channel = self.channel, author = self.target)
		if result is not None:
			raise UnexpectedResponseError

	async def wait_for_delete(self, message):
		pass # TODO: Implement this

	def check_failure_condition(self, message):
		''' When the bot we are testing does reply, make sure that it wasn't an internal
			error being reported.

			The current implementation is specific to MathBot. It will have to be changed
			if this library splits off as its own project.
		'''
		if 'Something went wrong while handling the message' in message.content:
			raise ErrordResponseError

	async def ask_human(self, query):
		''' Asks a human for an opinion on a question. Currently, only yes-no questions
			are supported. If the human answers 'no', the test will be failed.
		'''
		message = await self.client.send_message(self.channel, query)
		await self.client.add_reaction(message, u'\u2714')
		await self.client.add_reaction(message, u'\u274C')
		await asyncio.sleep(0.5)
		reaction = await self.client.wait_for_reaction(timeout = 20, message = message)
		if reaction is None:
			raise HumanResponseTimeout
		reaction, user = reaction
		if reaction.emoji == u'\u274C':
			raise HumanResponseFailure

	# async def wait_for_pm(self):
	# 	result = await self.client.wait_for_message(timeout = 20, channel = self.channel, author = self.target)
	# 	if result is None:
	# 		raise NoResponseError
	# 	return result


class Automata:

	def __init__(self):
		self.client = discord.Client()
		self.setup_done = False
		self.tests = []
		self.setup_tasks = []

	def test(self, needs_human = False, early_function = None):
		''' Creates a new test.
			This function is designed to be called as a decorator, but doesn't need to be.
		'''
		def applier(function):
			test = Test(function.__name__, function, needs_human = needs_human)
			assert self.find_test(test.name) is None
			self.tests.append(test)
		if early_function:
			applier(early_function)
		else:
			return applier

	def setup(self, early_function = None):
		''' Adds a new setup task.
			All setup tasks will be run before any test is attempted.
		'''
		def applier(function):
			assert not self.setup_done
			self.setup_tasks.append(function)
		if early_function:
			applier(early_function)
		else:
			return applier

	def find_test(self, name):
		''' Return a test with a given name. If no such test exists, return None '''
		for i in self.tests:
			if i.name == name:
				return i
		return None

	def run(self, token, target):

		''' Run automata.
			The token of the automata bot, and the name of the bot that you want to test.
			This call will block the program.
		'''

		@self.client.event
		async def on_message(message):
			# Find the target, if we can't find it, crash
			the_target = None
			for i in message.server.members:
				if target in i.name:
					the_target = i
			assert the_target is not None
			# Run test command
			if message.content.startswith('::run '):
				name = message.content[6:]
				print('Running test:', name)
				if name == 'all':
					await self.run_many(message, the_target)
				elif name == 'unrun':
					await self.run_many(message, the_target, lambda x : x.result is None)
				elif '*' in name:
					regex = re.compile(name.replace('*', '.*'))
					await self.run_many(message, the_target, lambda x : regex.fullmatch(x.name))
				elif self.find_test(name) is None:
					await self.client.send_message(message.channel, ':x: There is no test called `{}`'.format(name))
				else:
					await self.client.send_message(message.channel, 'Running test `{}`'.format(name))
					await self.run_test(self.find_test(name), message.channel, the_target)
					await self.display_stats(message.channel)
			# Status display command
			elif message.content == '::stats':
				await self.display_stats(message.channel)
			elif message.content == '::help':
				await self.client.send_message(message.channel, HELP_TEXT)

		@self.client.event
		async def on_ready():
			print('Started')

		self.client.run(token)

	async def run_many(self, message, the_target, condition = lambda x : True):
		''' Run all the tests that match some predicate. '''
		# All the tests that need a human should be run first.
		to_run = sorted(filter(condition, self.tests), key = lambda x : not x.needs_human)
		# Run all the tests and then display the stats
		for test in to_run:
			await self.client.send_message(message.channel, 'Running test `{}`'.format(test.name))
			await asyncio.sleep(0.5)
			await self.run_test(test, message.channel, the_target)
			await asyncio.sleep(0.5)
		await self.display_stats(message.channel)

	async def display_stats(self, channel):
		''' Display the status of the various tests. '''
		# NOTE: An emoji is the width of two spaces
		response = '```\n'
		longest_name = max(map(lambda x : len(x.name), self.tests))
		for test in self.tests:
			response += test.name.rjust(longest_name) + ' '
			if test.needs_human:
				response += '✋ '
			else:
				response += '   '
			if test.result is None:
				response += '⚫ Not run\n'
			elif test.result is True:
				response += '✔️ Passed\n'
			elif test.result is False:
				response += '❌ Failed\n'
		response += '```\n'
		await self.client.send_message(channel, response)

	async def run_test(self, test, channel, target):
		''' Run a single given test '''
		await self.ensure_setup(channel, target)
		test.result = False
		try:
			await test.func(Interface(self.client, channel, target))
			test.result = True
		except Exception as e:
			print('-------------------------------------------')
			print('Test failed:', test.name)
			print('-------------------------------------------')
			traceback.print_exc()

	async def ensure_setup(self, channel, target):
		try:
			if not self.setup_done:
				for task in self.setup_tasks:
					await task(Interface(self.client, channel, target))
					await asyncio.sleep(1)
				self.setup_done = True
		except Exception:
			await self.client_send_message(channel, 'An error occurred during setup. Test was not run.')
			raise
