import asyncio


ANY_EMOJI = '<any>'


class Command:

	def __init__(self, names, fmt, func, perm_setting, perm_default, no_dm, no_public):
		self.names = names.split(' ')
		self.name = self.names[0]
		self.format = fmt
		self.func = func
		self.perm_setting = perm_setting
		self.perm_default = perm_default
		self.on_edit = None
		self.require_before = True
		self.require_after = True
		self.no_dm = no_dm
		self.no_public = no_public

	def edit(self, require_before=True, require_after=True):
		self.require_before = require_before
		self.require_after = require_after
		''' Returns a decorator that can be used to hook an edit handler to the function '''
		def applier(function):
			self.on_edit = function
			return None # Not really sure if this is a good idea...
		return applier


class ReactionHandler:

	def __init__(self, func, emoji, allow_self):
		self.func = func
		self.emoji = emoji
		self.allow_self = allow_self


class BackgroundTask:

	def __init__(self, func):
		self.func = func


class StartupTask:

	def __init__(self, func):
		self.func = func


# Events allow a module to get events straight from the system
class Event:

	def __init__(self, name, func):
		self.name = name
		self.func = func


class OnMessage:

	def __init__(self, func):
		self.func = func


class OnEdit:

	def __init__(self, func):
		self.func = func


class OnMemberJoined:

	def __init__(self, func, servers = None):
		self.func = func
		self.servers = servers


def command(name: str, fmt: str, *, perm_setting=None, perm_default=None, no_dm=False, no_public=False) -> Command:
	''' Flags a function as a command.
		name - the name of the command, so it will be invoked with =name
		fmt - the argument format specification, use * to just grab the entire string.
		perm_setting - Permissions setting.
		perm_default - Override for the default value of the permission.
		no_dm - Specifies that a command cannot be used in private channels.
		no_public - Specifies that a command cannot be used in public channels.
	'''
	if not isinstance(name, str):
		raise TypeError('Command names should be strings')
	if not isinstance(fmt, str):
		raise TypeError('Command argument format specifiers should be strings')
	def applier(func):
		return Command(name, fmt, func, perm_setting, perm_default, no_dm, no_public)
	return applier


def background_task(requires_ready = True):
	def applier(func):
		if requires_ready:
			async def wrapper(self, *args, **kwargs):
				while not self.client._core_ready:
					await asyncio.sleep(5)
				await func(self, *args, **kwargs)
			return BackgroundTask(wrapper)
		return BackgroundTask(func)
	return applier


def startup_task():
	def applier(func):
		return StartupTask(func)
	return applier


def event(name):
	assert(isinstance(name, str))
	def applier(func):
		return Event(name, func)
	return applier


def on_message():
	def applier(func):
		return OnMessage(func)
	return applier


def on_edit():
	def applier(func):
		return OnEdit(func)
	return applier


def on_member_joined(servers = None):
	def applier(func):
		return OnMemberJoined(func, servers = servers)
	return applier


def add_reaction(emoji = ANY_EMOJI, allow_self = False):
	def applier(func):
		return ReactionHandler(func, emoji, allow_self)
	return applier


# I don't think this belongs here
class Redirect:
	''' Return this from a command to redirect the command
		to another handler.
	'''

	def __init__(self, *destination):
		self.destination = ' '.join(destination)
