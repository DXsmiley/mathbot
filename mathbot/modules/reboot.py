from discord.ext.commands import command, Cog, Context
import typing

if typing.TYPE_CHECKING:
	from bot import MathBot


class Reboot(Cog):

	# Used to have an actual "reboot" command but we're no longer on Heroku so I just deleted it

	@command()
	async def sync_commands_global(self, ctx: 'Context[MathBot]'):
		# TODO: Make this userid set in parameters.json
		if ctx.author.id == 133804143721578505:
			await ctx.send('Syncing global commands')
			async with ctx.typing():
				print('Syncing global commands...')
				await ctx.bot.tree.sync()
				print('Done')
				await ctx.send('Done')

def setup(bot: 'MathBot'):
	return bot.add_cog(Reboot())
