from discord.ext.commands import command, Cog
import subprocess
import modules.reporter

class Reboot(Cog):

	@command()
	async def reboot(self, ctx):
		if ctx.author.id in ctx.bot.parameters.getd('reboot.allowed', []):
			app = ctx.bot.parameters.get('reboot.app')
			api_key = ctx.bot.parameters.get('reboot.heroku_key')
			m = f'{ctx.author.mention} ({ctx.author}) is restarting the bot'
			print(m)
			await modules.reporter.report(ctx.bot, m)
			await ctx.send('Restarting bot')
			subprocess.Popen([
				'curl', '-n', '-X', 'DELETE',
				f'https://api.heroku.com/apps/{app}/dynos',
				'-H', 'Content-Type: application/json',
				'-H', 'Accept: application/vnd.heroku+json; version=3',
				'-H', f'Authorization: Bearer {api_key}'
			])

def setup(bot):
	bot.add_cog(Reboot())
