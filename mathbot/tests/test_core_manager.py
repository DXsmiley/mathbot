import pytest
import core.module
import core.manager
import core.handles
import core.keystore
import discord


core.keystore.setup_disk(None)


class ExampleModule(core.module.Module):

	@core.handles.command('echo', '*')
	async def echo(self, message, contents):
		pass


class ConflictingModule(core.module.Module):

	@core.handles.command('echo', '*')
	async def another_echo(self, message, contents):
		pass # pragma: no cover


class AnotherModule(core.module.Module):

	@core.handles.command('hello', '*')
	async def hello(self, message, contents):
		pass # pragma: no cover


@pytest.fixture(scope = 'function')
def manager():
	return core.manager.Manager('token')


def test_command_collection(manager):
	manager.add_modules(ExampleModule(), AnotherModule())
	manager.setup()
	assert manager.commands['echo'] == ExampleModule.echo
	assert manager.commands['hello'] == AnotherModule.hello


def test_duplicate_command(manager):
	manager.add_modules(ExampleModule())
	manager.add_modules(ConflictingModule())
	with pytest.raises(core.manager.CommandConflictError):
		manager.setup()


class MockChannel(discord.Channel):

	def __init__(self, is_private):
		self.is_private = is_private


class MockServer(discord.Server):

	def __init__(self):
		self.id = '0000000000000000'


class MockMessage(discord.Message):

	def __init__(self, content):
		self.content = content
		self.channel = MockChannel(False)
		self.server = MockServer()
		self.author = MockUser()


class MockUser: # pylint: disable=too-few-public-methods
	''' A mock object representing a user.
		Contains the bare minimum amount of information
		required to pass the tests.
	'''

	def __init__(self):
		self.perms = discord.Permissions.none()
		self.id = '012345678901234567' # pylint: disable=invalid-name

	def permissions_in(self, channel):
		''' Returns the permissions that a user would have if they
			were operating in a given channel.
		'''
		assert isinstance(channel, MockChannel)
		return self.perms


@pytest.mark.asyncio
async def test_message_handler(manager): # pylint: disable=redefined-outer-name
	manager.add_modules(ExampleModule())
	manager.setup()
	await manager.handle_message(MockMessage('=echo'))
