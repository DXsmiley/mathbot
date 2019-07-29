''' Module used to send help documents to users. '''

import re
import core.help
from discord.ext.commands import command
import discord
from utils import is_private


SERVER_LINK = 'https://discord.gg/JbJbRZS'
PREFIX_MEMORY_EXPIRE = 60 * 60 * 24 * 3 # 3 days


def doubleformat(string, **replacements):
	''' Acts a but like format, but works on things wrapped in *two* curly braces. '''
	for key, value in replacements.items():
		string = string.replace('{{' + key + '}}', value)
	return string


class HelpModule:
	''' Module that serves help pages. '''

	@command()
	async def support(self, context):
		await context.send(f'Mathbot support server: {SERVER_LINK}')

	@command()
	async def invite(self, context):
		await context.send('Add mathbot to your server: https://dxsmiley.github.io/mathbot/add.html')

	@command()
	async def help(self, context, *, topic='help'):
		await self.handle_help(context, topic, context.lang)

	@command(aliases=['help-en'])
	async def help_en(self, context, *, topic='help'):
		await self.handle_help(context, topic, 'en')

	async def handle_help(self, context, topic, language):
		''' Help command itself.
			Help is sent via DM, but a small message is also sent in the public chat.
			Specifying a non-existent topic will show an error and display a list
			of topics that the user could have meant.
		'''
		if topic in ['topics', 'topic', 'list']:
			return await self._send_topic_list(context)

		found_doc, did_fallback = core.help.get(topic, language=language)
		if found_doc is None:
			await context.send(self._suggest_topics(topic))
			return

		if did_fallback:
			await context.message.author.send(embed = discord.Embed(
				title='This help page is not available in your language yet',
				description=f'If you want to help translate documents, talk to us on the mathbot server: {SERVER_LINK}'
			))

		# Display the default prefix if the user is in DMs and uses no prefix.
		prefix = context.prefix or '='
		
		try:
			for index, page in enumerate(found_doc):
				page = doubleformat(
					page,
					prefix=prefix,
					mention=context.bot.user.mention,
					add_link='https://dxsmiley.github.io/mathbot/add.html',
					server_link=SERVER_LINK,
					patreon_link='https://www.patreon.com/dxsmiley',
					patreon_listing=await context.bot.get_patron_listing()
				)
				await context.message.author.send(page)
		except discord.Forbidden:
			await context.send(embed=discord.Embed(
				title='The bot was unable to slide into your DMs',
				description=f'Please try modifying your privacy settings to allow DMs from server members. If you are still experiencing problems, contact the developer at the mathbot server: {SERVER_LINK}',
				colour=discord.Colour.red()
			))

	async def _send_topic_list(self, context):
		topics = core.help.listing()
		column_width = max(map(len, topics))
		columns = 3
		reply = 'The following help topics exist:\n```\n'
		for i, t in enumerate(topics):
			reply += t.ljust(column_width)
			reply += '\n' if (i + 1) % columns == 0 else '  ';
		reply += '```\n'
		await context.send(reply)

	def _suggest_topics(self, typo):
		suggestions = core.help.get_similar(typo)
		if not suggestions:
			return f"Help topic `{typo}` does not exist."
		elif len(suggestions) == 1:
			return f"Help topic `{typo}` does not exist.\nMaybe you meant `{suggestions[0]}`?"
		return f"Help topic `{typo}` does not exist.\nMaybe you meant one of: {', '.join(map('`{}`'.format, suggestions))}?"

def setup(bot):
	bot.add_cog(HelpModule())
