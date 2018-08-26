import sys
import functools
import discord
import io


class MessageEditedException(Exception):
	pass


class MessageEditGuard:

	def __init__(self, message):
		self._message = message
		self._start_timestamp = self._get_timestamp()

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		return isinstance(value, MessageEditGuard)

	def _get_timestamp(self):
		return self._message.edited_at or self._message.created_at

	async def send(self, *args, **kwargs):
		if self._get_timestamp() != self._start_timestamp:
			print('Edit guard prevented sending of message')
			raise MessageEditedException
		return await self._message.channel.send(*args, **kwargs)


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
