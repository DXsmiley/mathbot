import sys
import functools
import discord
import io
import core.blame


class MessageEditedException(Exception):
	pass


class MessageEditGuard:
	''' Used to handle message cleanup for commands that
		may be edited in order to re-invoke them.
	'''

	def __init__(self, trigger, destination, bot):
		self._trigger = trigger
		self._destination = destination
		self._bot = bot
		self._start_timestamp = self._get_timestamp()

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		return isinstance(value, MessageEditGuard)

	def _get_timestamp(self):
		return self._trigger.edited_at or self._trigger.created_at

	async def send(self, *args, **kwargs):
		if self._get_timestamp() != self._start_timestamp:
			print('Edit guard prevented sending of message')
			raise MessageEditedException
		sent_message = await self._destination.send(*args, **kwargs)
		self._bot.message_link(self._trigger, sent_message)
		await core.blame.set_blame(self._bot.keystore, sent_message, self._trigger.author)
		return sent_message


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
