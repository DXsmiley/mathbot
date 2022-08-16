import core.help
import discord
import asyncio


from discord.ext.commands import guild_only, has_permissions, Cog, Context
from discord.ext.commands.hybrid import hybrid_command


USER_PERM_ERROR = '''\
You do not have the permissions required to perform that operation in this channel.
You need to have permission to *manage messages*.
'''

PRIVATE_ERROR = '''\
The `=purge` command cannot be used in a private channel.
See `=help purge` for more details.
'''

core.help.load_from_file('./help/purge.md')

class PurgeModule(Cog):
	@hybrid_command()
	@guild_only()
	@has_permissions(manage_messages=True)
	async def purge(self, ctx, number: int):
		if number > 0:
			number = min(200, number)
			async for message in ctx.channel.history(limit=200):
				if message.author.id == ctx.bot.user.id and number > 0:
					try:
						await message.delete()
						number -= 1
					except discord.errors.NotFound:
						pass
					await asyncio.sleep(1)

def setup(bot):
	return bot.add_cog(PurgeModule())
