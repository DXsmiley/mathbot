import sys
import functools
import discord
from discord.ext.commands import Context
import io
import core.blame


class MessageEditedException(Exception):
	pass


class MessageEditGuard:
	''' Used to handle message cleanup for commands that
		may be edited in order to re-invoke them.
	'''

	def __init__(self, message, destination, bot):
		self._message = message
		self._destination = destination
		self._bot = bot
		self._initial_content = self._message.clean_content

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		return isinstance(value, MessageEditedException)

	async def send(self, *args, **kwargs):
		if self._initial_content != self._message.clean_content:
			print('Edit guard prevented sending of message')
			raise MessageEditedException
		return await self._bot.send_patch(self._message, self._destination.send)(*args, **kwargs)

	async def reply(self, context: Context, *args, **kwargs):
		if self._initial_content != self._message.clean_content:
			print('Edit guard prevented sending of message')
			raise MessageEditedException
		# TODO: Handle blame
		return await context.reply(*args, **kwargs)


def listify(function):
	@functools.wraps(function)
	def wrapper(*args, **kwargs):
		return list(function(*args, **kwargs))
	return wrapper


def apply(*functions):
	def decorator(internal):
		@functools.wraps(internal)
		def wrapper(*args, **kwargs):
			result = internal(*args, **kwargs)
			for i in functions[::-1]:
				result = i(result)
			return result
		return wrapper
	return decorator


def err(*args, **kwargs):
	return print(*args, **kwargs, file=sys.stderr)


def is_private(channel):
	return isinstance(channel, discord.abc.PrivateChannel)


def image_to_discord_file(image, fname):
	''' Converts a PIL image to a discord.File object,
		so that it may be sent over the internet.
	'''
	fobj = io.BytesIO()
	image.save(fobj, format='PNG')
	fobj = io.BytesIO(fobj.getvalue())
	return discord.File(fobj, fname)
