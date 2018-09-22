import functools

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
