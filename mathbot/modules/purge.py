import core.help
import discord
import asyncio
from utils import is_private
from core.util import invoker_requires_perms


from discord.ext.commands import command, guild_only

USER_PERM_ERROR = '''\
You do not have the permissions required to perform that operation in this channel.
You need to have permission to *manage messages*.
'''

PRIVATE_ERROR = '''\
The `=purge` command cannot be used in a private channel.
See `=help purge` for more details.
'''

core.help.load_from_file('./help/purge.md')

class PurgeModule:
	@command()
	@guild_only()
	@invoker_requires_perms('manage_messages')
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
	bot.add_cog(PurgeModule())
