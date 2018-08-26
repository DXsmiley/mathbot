import functools

import discord
import discord.ext.commands

permission_attributes = [
	'create_instant_invite',
	'kick_members',
	'ban_members',
	'administrator',
	'manage_channels',
	'manage_server',
	'add_reactions',
	'view_audit_logs',
	'read_messages',
	'send_messages',
	'send_tts_messages',
	'manage_messages',
	'embed_links',
	'attach_files',
	'read_message_history',
	'mention_everyone',
	'external_emojis',
	'connect',
	'speak',
	'mute_members',
	'deafen_members',
	'move_members',
	'use_voice_activation',
	'change_nickname',
	'manage_nicknames',
	'manage_roles',
	'manage_webhooks',
	'manage_emojis'
]

def permission_names(perm):
	for i in permission_attributes:
		if getattr(perm, i):
			yield i.replace('_', ' ').title()

# Decorator to make command respond with whatever the command returns
def respond(coro):
	@functools.wraps(coro)
	async def internal(self, ctx, *args, **kwargs):
		result = await coro(self, ctx, *args, **kwargs)
		if result is not None:
			await ctx.send(result)
	return internal

def invoker_requires_perms(*perms):
	p = discord.Permissions()
	p.update(**{i: True for i in perms})
	def predicate(ctx):
		x = ctx.channel.permissions_for(ctx.author)
		print(p, x, p.is_subset(x))
		return p.is_subset(x)
	return discord.ext.commands.check(predicate)
