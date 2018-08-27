import functools

import discord
import discord.ext.commands

def permission_names(perm):
	for permission, has in perm:
		if has:
			yield permission.replace('_', ' ').title()

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
