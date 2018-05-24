# Has a command which echoes whatever text was given to it.
# Used only for testing purposes.

from discord.ext.commands import command


class EchoModule:

	def __init__(self, bot):
		self.bot = bot

	@command()
	async def echo(self, context, *, text: str):
		await context.send(text)


def setup(bot):
	bot.add_cog(EchoModule(bot))
