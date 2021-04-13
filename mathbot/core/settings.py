import core.keystore
import warnings
import discord
import discord.ext.commands

class None2:
	pass


SETTINGS = {
	'c-tex': {'default': True},
	'c-calc': {'default': True},
	'c-wolf': {'default': True},
	'c-roll': {'default': True},
	'c-oeis': {'default': True},
	'f-calc-shortcut': {'default': True},
	'f-wolf-filter': {'default': True},
	'f-wolf-mention': {'default': True},
	'f-inline-tex': {'default': False},
	'f-delete-tex': {'default': False},
	'f-tex-inline': {'redirect': 'f-inline-tex', 'cannon-name': True},
	'f-tex-delete': {'redirect': 'f-delete-tex', 'cannon-name': True},
	'f-tex-trashcan': {'default': True},
	'f-roll-unlimited': {'default': False},
	'm-disabled-cmd': {'default': True},
	'x-bonus': {'default': True},
}


class Settings:

	def __init__(self, keystore):
		self.keystore = keystore

	def _get_key(self, setting, context):
		setting = redirect(setting)
		if not isinstance(setting, str):
			raise TypeError(f'{setting} is not a valid setting')
		if isinstance(context, discord.TextChannel):
			return f'{setting}:{context.id}' + ('c' if context.guild.id == context.id else '')
		# if isinstance(context, discord.DMChannel):
		# 	return f'{setting}:{context.id}'
		if isinstance(context, discord.Guild):
			return f'{setting}:{context.id}'
		raise TypeError('Type {context.__class__} if not a valid settings context')

	async def get_single(self, setting, context):
		return await self.keystore.get(self._get_key(setting, context))

	async def resolve(self, setting, *contexts, default=None2):
		setting = redirect(setting)
		for i in contexts:
			result = await self.get_single(setting, i)
			if result is not None:
				return result
		if default is not None2:
			return default
		return SETTINGS[setting]['default']

	async def resolve_message(self, setting, message):
		setting = redirect(setting)
		if isinstance(message.channel, discord.DMChannel):
			so = SETTINGS[setting]
			return so.get('private', so['default'])
		if isinstance(message.channel, discord.TextChannel):
			return await self.resolve(setting, message.channel, message.channel.guild)
		raise ValueError(f'{message} cannot be resolved for settings')

	async def set(self, setting, context, value):
		setting = redirect(setting)
		key = self._get_key(setting, context)
		print(key, '==>', value)
		if value is None:
			await self.keystore.delete(key)
		elif value not in [0, 1]:
			raise ValueError(f'{value} is not a valid setting value')
		else:
			await self.keystore.set(key, value)

	async def get_server_prefix(self, context):
		if isinstance(context, discord.Message):
			context = context.channel
		if isinstance(context, discord.DMChannel):
			return '='
		if isinstance(context, discord.TextChannel):
			context = context.guild
		if not isinstance(context, discord.Guild):
			raise TypeError(f'{context} is not a valid context for the server prefix')
		stored = await self.keystore.get(f's-prefix:{context.id}')
		return '=' if stored is None else stored

	async def set_server_prefix(self, context, prefix):
		if isinstance(context, discord.Message):
			context = context.channel
		if isinstance(context, discord.TextChannel):
			context = context.guild
		if not isinstance(context, discord.Guild):
			raise TypeError(f'{context} is not a valid guild.')
		return (await self.keystore.set(f's-prefix:{context.id}', prefix)) or '='

def _get_key(setting, context):
	setting = redirect(setting)
	if not isinstance(setting, str):
		raise TypeError('{} is not a valid setting'.format(setting))
	if isinstance(context, discord.TextChannel):
		if not context.is_private and context.id == context.server.id:
			return f'{setting}:{context.id}c'
		else:
			return f'{setting}:{context.id}'
	if isinstance(context, discord.Server):
		return f'{setting}:{context.id}'
	raise TypeError('Type {} is not a valid settings context'.format(context.__class__))


async def get_single(setting, context):
	raise Exception('setting is deprecated and cannot be used')
	setting = redirect(setting)
	return await core.keystore.get(_get_key(setting, context))


async def resolve(setting, *contexts, default = None2):
	raise Exception('setting is deprecated and cannot be used')
	if not isinstance(setting, str):
		raise TypeError('First argument of core.settings.resolve(setting, *contexts) should be a string.')
	setting = redirect(setting)
	for i in contexts:
		result = await get_single(setting, i)
		if result is not None:
			return result
	if default is not None2:
		return default
	return SETTINGS[setting]['default']


async def resolve_message(setting, message):
	raise Exception('resolve_message is deprecated and cannot be used')
	setting = redirect(setting)
	if message.channel.is_private:
		so = SETTINGS[setting]
		if 'private' in so:
			return so['private']
		return so['default']
	return await resolve(setting, message.channel, message.server)


async def get_setting(message, setting):
	raise Exception('message is deprecated and cannot be used')
	warnings.warn('core.settings.get_setting is deprecated', stacklevel = 2)
	return await resolve_message(setting, message)


async def set(setting, context, value):
	raise Exception('set is deprecated and cannot be used')
	setting = redirect(setting)
	key = _get_key(setting, context)
	print(key, '--->', value)
	if value is None:
		await core.keystore.delete(key)
	elif value not in [0, 1]:
		raise ValueError('{} is not a valid setting value'.format(value))
	else:
		await core.keystore.set(key, value)


async def get_server_prefix(context):
	raise Exception('get_server_prefix is deprecated and cannot be used')
	if isinstance(context, discord.message.Message):
		context = context.channel
	if isinstance(context, discord.abc.PrivateChannel):
		return '='
	if isinstance(context, discord.channel.TextChannel):
		if context.is_private:
			return '='
		context = context.server
	if not isinstance(context, discord.Server):
		raise TypeError('{} is not a valid server'.format(context))
	stored = await core.keystore.get('s-prefix:' + context.id)
	return '=' if stored is None else str(stored)


async def set_server_prefix(context, prefix):
	raise Exception('set_server_prefix is deprecated and cannot be used')
	if isinstance(context, discord.Message):
		context = context.channel
	if isinstance(context, discord.TextChannel):
		if context.is_private:
			return '='
		context = context.server
	if not isinstance(context, discord.Server):
		raise TypeError('{} is not a valid server'.format(context))
	return (await core.keystore.set('s-prefix:' + context.id, prefix)) or '='


async def get_channel_prefix(channel):
	raise Exception('get_channel_prefix is deprecated and cannot be used')
	if channel.is_private:
		return '='
	return await get_server_prefix(channel.server)


def redirect(setting):
	if setting not in SETTINGS:
		return None
	next = SETTINGS[setting].get('redirect')
	if next:
		return redirect(next)
	return setting


def details(setting):
	return SETTINGS.get(redirect(setting))

def get_cannon_name(setting):
	if setting not in SETTINGS:
		raise KeyError(f'{setting} is not a valid setting')
	for name, details in SETTINGS.items():
		if details.get('redirect', name) == setting and details.get('cannon-name'):
			return name
	return setting


class DisabledCommandByServerOwner(discord.ext.commands.CheckFailure): pass
class DisabledCommandByServerOwnerSilent(discord.ext.commands.CheckFailure): pass


async def raise_if_command_disabled(bot, message, setting):
	if not await bot.settings.resolve_message(setting, message):
		if await bot.settings.resolve_message('m-disabled-cmd', message):
			raise DisabledCommandByServerOwner
		else:
			raise DisabledCommandByServerOwnerSilent


# Maybe move this to some other file??
def command_allowed(setting):
	async def predicate(context):
		await raise_if_command_disabled(context.bot, context.message, setting)
		return True
	return discord.ext.commands.check(predicate)
