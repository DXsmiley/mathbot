from discord.ext.commands import command

class ThrowsModule:

	@command()
	async def throw(self, context):
		raise Exception('I wonder what went wrong?')

def setup(bot):
	bot.add_cog(ThrowsModule())
