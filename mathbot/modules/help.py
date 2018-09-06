''' Module used to send help documents to users. '''

import re
import core.help
from discord.ext.commands import command
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
	async def help(self, context, *, topic='help'):
		''' Help command itself.
			Help is sent via DM, but a small message is also sent in the public chat.
			Specifying a non-existent topic will show an error and display a list
			of topics that the user could have meant.
		'''
		if topic in ['topics', 'topic', 'list']:
			return await self._send_topic_list(context)

		found_doc = core.help.get(topic)
		if found_doc is None:
			await context.send(self._suggest_topics(topic))
			return

		# Display the default prefix if the user is in DMs and uses no prefix.
		prefix = context.prefex or '='
		
		was_private = True
		
		for index, page in enumerate(found_doc):
			page = doubleformat(
				page,
				prefix=prefix,
				mention=context.bot.user.mention,
				add_link='https://discordapp.com/oauth2/authorize?&client_id=172236682245046272&scope=bot&permissions=126016', # pylint: disable=line-too-long
				server_link=SERVER_LINK
			)
			# TODO: Handle users who are unable to receive private messages.
			await context.message.author.send(page)
			# await self.send_message(msg, page)
			# args = [msg.author, msg.channel, page]
			# if not await self.send_private_fallback(*args, supress_warning=index > 0):
			# 	was_private = False
		
		if was_private and not is_private(context.channel):
			if topic:
				reply = "Information on `{}` has been sent to you privately.".format(topic)
			else:
				reply = "Help has been sent to you privately."
			await context.send(reply)

	async def _send_topic_list(self, context):
		# TODO: Get this working again
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
