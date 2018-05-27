import sys
import functools
import discord

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
