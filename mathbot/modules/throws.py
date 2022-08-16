from discord.ext.commands import command, Cog

class ThrowsModule(Cog):

	@command()
	async def throw(self, context):
		raise Exception('I wonder what went wrong?')

def setup(bot):
	return bot.add_cog(ThrowsModule())
