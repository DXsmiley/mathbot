import core.keystore
import expiringdict
import discord


def _get_key(setting, context):
	if isinstance(context, discord.Channel):
		if not context.is_private and context.id == context.server.id:
			key = '{setting}:{id}c'
		else:
			key = '{setting}:{id}'
		return key.format(setting = setting, id = context.id)
	if isinstance(context, discord.Server):
		key = '{setting}:{id}'
		return key.format(setting = setting, id = context.id)
	raise TypeError('Type {} is not a valid settings context'.format(context.__class__))


async def get_single(setting, context):
	await core.keystore.get(_get_key(setting, context))


async def resolve(setting, *contexts):
	for i in contexts:
		result = await get_single(setting, i)
		if result is not None:
			return result
	return SETTINGS[setting]['default']


async def resolve_message(setting, message):
	if message.channel.is_private:
		so = SETTINGS[setting]
		if 'private' in so:
			return so['private']
		return so['default']
	return await resolve(setting, message.channel, message.server)


async def set(setting, context, value):
	key = _get_key(setting, context)
	if value is None:
		await core.keystore.delete(key)
	else:
		await core.keystore.set(_get_key(setting, context), value)


async def get_server_prefix(server):
	if not isinstance(server, discord.Server):
		raise TypeError
	return get_single('s-prefix', server) or '='


async def get_channel_prefix(channel):
	if channel.is_private:
		return '='
	return await get_server_prefix(channel.server)
