''' Automata is a small library designed to help with the
	creation of bots to test other bots. This is currently
	part of the MathBot project but if it gains enough
	traction I might fork it into its own repository
	Interfacing with the bot through discord:

	::stats
		Gives details about which tests have been
		run and what the results were

	::run test_name
		Run a particular test

	::run all
		Run all tests

	::run unrun
		Run all tests that have not yet been run

	::run failed
		Run all tests that failed on the most recent run

'''


import traceback
import asyncio
import re
import enum

import discord


TIMEOUT = 20


HELP_TEXT = '''\
**::help** - Show this help
**::run** all - Run all tests
**::run** unrun - Run all tests that have not been run
**::run** *name* - Run a specific test
'''


SPECIAL_TEST_NAMES = {'all', 'unrun', 'failed'}


class TestRequirementFailure(Exception):
	''' Base calss for the errors that are raised when an expectation is not met '''

class NoResponseError(TestRequirementFailure):
	''' Raised when the target bot fails to respond to a message '''

class UnexpectedResponseError(TestRequirementFailure):
	''' Raised when the target bot failed to stay silent '''

class ErrordResponseError(TestRequirementFailure):
	''' Raised when the target bot produced an error message '''

class UnexpectedSuccessError(TestRequirementFailure):
	''' Raised when the target bot failed to produce an error message '''

class HumanResponseTimeout(TestRequirementFailure):
	''' Raised when a human fails to assert the result of a test '''

class HumanResponseFailure(TestRequirementFailure):
	''' Raised when a human fails a test '''

class ResponseDidntMatch(TestRequirementFailure):
	''' Raised when the target bot responds with a message that doesn't meet criteria '''


class TestResult(enum.Enum):
	''' Enum representing the result of running a test case '''
	UNRUN = 0
	SUCCESS = 1
	FAILED = 2


class Test:

	''' Holds data about a specific test '''

	def __init__(self, name: str, func, needs_human: bool = False) -> None:
		if name in SPECIAL_TEST_NAMES:
			raise ValueError('{} is not a valid test name'.format(name))
		self.name = name # The name of the test
		self.func = func # The function to run when running the test
		self.last_run = 0 # When the test was last run
		self.result = TestResult.UNRUN # The result of the test (True or False) or None if it was not run
		self.needs_human = needs_human # Whether the test requires human interation


class Interface:

	''' The interface that the test functions should use to interface with discord.
		Test functions should not access the discord.py client directly.
	'''

	def __init__(self,
				 client: discord.Client,
				 channel: discord.Channel,
				 target: (discord.Member, discord.User)) -> None:
		self.client = client # The discord.py client object
		self.channel = channel # The channel the test is running in
		self.target = target # The bot which we are testing

	async def send_message(self, content):
		''' Send a message to the testing channel. '''
		return await self.client.send_message(self.channel, content)

	async def edit_message(self, message, new_content):
		''' Modified a message. Doesn't actually care what this message is. '''
		return await self.client.edit_message(message, new_content)

	async def wait_for_message(self):
		''' Waits for the bot the send a message.
			If the bot takes longer than 20 seconds, the test fails.
		'''
		result = await self.client.wait_for_message(
			timeout=TIMEOUT,
			channel=self.channel,
			author=self.target)
		if result is None:
			raise NoResponseError
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
		# print('Sending...')
		await self.send_message(contents)
		# print('About to wait...')
		response = await self.wait_for_message()
		# print('Got response')
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
		result = await self.client.wait_for_message(
			timeout=TIMEOUT,
			channel=self.channel,
			author=self.target)
		if result is not None:
			raise UnexpectedResponseError

	async def ask_human(self, query):
		''' Asks a human for an opinion on a question. Currently, only yes-no questions
			are supported. If the human answers 'no', the test will be failed.
		'''
		message = await self.client.send_message(self.channel, query)
		await self.client.add_reaction(message, u'\u2714')
		await self.client.add_reaction(message, u'\u274C')
		await asyncio.sleep(0.5)
		reaction = await self.client.wait_for_reaction(timeout=TIMEOUT, message=message)
		if reaction is None:
			raise HumanResponseTimeout
		reaction, _ = reaction
		if reaction.emoji == u'\u274C':
			raise HumanResponseFailure


class ExpectCalls: # pylint: disable=too-few-public-methods

	''' Wrap a function in an object which counts the number
		of times it was called. If the number of calls is not
		equal to the expected number when this object is
		garbage collected, something has gone wrong, and in
		that case an error is thrown.
	'''

	def __init__(self, function, expected_calls=1):
		self.function = function
		self.expected_calls = expected_calls
		self.call_count = 0

	def __call__(self, *args, **kwargs):
		self.call_count += 1
		return self.function(*args, **kwargs)

	def __del__(self):
		if self.call_count != self.expected_calls:
			message = '{} was called {} times. It was expcted to have been called {} times'
			raise RuntimeError(message.format(self.function, self.call_count, self.expected_calls))


class TestCollector:

	''' Used to group tests and pass them around all at once. '''

	def __init__(self):
		self._tests = []

	def add(self, function, name: str = '', needs_human: bool = False):
		''' Adds a test function to the group. '''
		name = name or function.__name__
		test = Test(name, function, needs_human=needs_human)
		if name in self._tests:
			raise KeyError('A test case called {} already exists.'.format(name))
		self._tests.append(test)

	def find_by_name(self, name: str):
		''' Return the test with the given name.
			Return None if it does not exist.
		'''
		for i in self._tests:
			if i.name == name:
				return i
		return None

	def __call__(self, *args, **kwargs):
		''' Add a test decorator-style. '''
		def _decorator(function):
			self.add(function, *args, **kwargs)
		return ExpectCalls(_decorator, 1)

	def __iter__(self):
		return (i for i in self._tests)


class DiscordBot(discord.Client):

	''' Discord bot used to run tests.
		This class by itself does not provide any useful methods for human interaction.
	'''

	def __init__(self, target_name: str) -> None:
		super().__init__()
		self._target_name = target_name.lower()
		# self._setup_done = False

	def _find_target(self, server: discord.Server) -> discord.Member:
		for i in server.members:
			if self._target_name in i.name.lower():
				return i
		raise KeyError('Could not find memory with name {}'.format(self._target_name))

	async def run_test(self,
		               test: Test,
		               channel: discord.Channel,
		               stop_error: bool = False) -> TestResult:
		''' Run a single test in a given channel.
			Updates the test with the result, and also returns it.
		'''
		interface = Interface(
			self,
			channel,
			self._find_target(channel.server))
		try:
			await test.func(interface)
		except TestRequirementFailure:
			test.result = TestResult.FAILED
			if not stop_error:
				raise
		else:
			test.result = TestResult.SUCCESS
		return test.result


class DiscordUI(DiscordBot):

	''' A variant of the discord bot which supports additional commands
		to allow a human to also interact with it.
	'''

	def __init__(self, target_name: str, tests: TestCollector) -> None:
		super().__init__(target_name)
		self._tests = tests

	async def _run_by_predicate(self, channel, prediate):
		for test in self._tests:
			if prediate(test):
				await self.send_message(channel, '**Running test {}**'.format(test.name))
				await self.run_test(test, channel, stop_error=True)

	async def _display_stats(self, channel: discord.Channel) -> None:
		''' Display the status of the various tests. '''
		# NOTE: An emoji is the width of two spaces
		response = '```\n'
		longest_name = max(map(lambda t: len(t.name), self._tests))
		for test in self._tests:
			response += test.name.rjust(longest_name) + ' '
			if test.needs_human:
				response += '✋ '
			else:
				response += '   '
			if test.result is TestResult.UNRUN:
				response += '⚫ Not run\n'
			elif test.result is TestResult.SUCCESS:
				response += '✔️ Passed\n'
			elif test.result is TestResult.FAILED:
				response += '❌ Failed\n'
		response += '```\n'
		print(response)
		await self.send_message(channel, response)

	async def on_ready(self) -> None:
		''' Report when the bot is ready for use '''
		print('Started automata bot.')
		print('Available tests are:')
		for i in self._tests:
			print('   {}'.format(i.name))

	async def on_message(self, message: discord.Message) -> None:
		''' Handle an incomming message '''
		if not message.channel.is_private:
			if message.content.startswith('::run '):
				name = message.content[6:]
				print('Running test:', name)
				if name == 'all':
					await self._run_by_predicate(message.chanel, lambda t: True)
				elif name == 'unrun':
					pred = lambda t: t.result is TestResult.UNRUN
					await self._run_by_predicate(message.channel, pred)
				elif name == 'failed':
					pred = lambda t: t.result is TestResult.FAILED
					await self._run_by_predicate(message.channel, pred)
				elif '*' in name:
					regex = re.compile(name.replace('*', '.*'))
					await self.run_many(message, lambda t: regex.fullmatch(t.name))
				elif self._tests.find_by_name(name) is None:
					text = ':x: There is no test called `{}`'
					await self.send_message(message.channel, text.format(name))
				else:
					await self.send_message(message.channel, 'Running test `{}`'.format(name))
					await self.run_test(self._tests.find_by_name(name), message.channel)
					await self._display_stats(message.channel)
			# Status display command
			elif message.content == '::stats':
				await self._display_stats(message.channel)
			elif message.content == '::help':
				await self.send_message(message.channel, HELP_TEXT)
