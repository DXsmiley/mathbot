# Used to keep track of who was responsible for causing the bot to send
# a particular message. This exists because people can use the =tex
# command then delete their message to get the bot to say offensive or
# innapropriate things. This allows server moderators (or anyone else really)
# to track down the person responsible

import core.help
from discord.ext.commands import command
from discord import Embed, Colour



MESSAGE_NOTHING_RECENT_FOUND = "No recent message was found."
MESSAGE_NOT_FOUND = "Couldn't find who was resposible for that :confused:"
MESSAGE_INVALID_ID = "`{}` is not a valid message ID"
MESSAGE_BLAME = '{} was responsible for that message.'


def is_message_id(s):
	return s.isnumeric()


class BlameModule:

	@command()
	async def blame(self, context, message_id: str):
		
		response = Embed(
			description='Argument was not a valid message ID',
			colour = Colour.red()
		)
		
		if message_id == 'recent':
			response = Embed(
				description='Could not find any recent message',
				colour = Colour.red()
			)
			async for m in context.channel.history(limit=100):
				if m.author == context.bot.user:
					user = await context.bot.keystore.get('blame', str(m.id))
					if user is None: continue
					response = Embed(
						description=f'{user} was responsible for the most recent message in this channel.',
						colour = Colour.blue()
					)
					break
		
		elif is_message_id(message_id):
			user = await context.bot.keystore.get('blame', message_id)
			if user is None:
				response = Embed(
					description='Could not find the blame information for that message',
					colour = Colour.red()
				)
			else:
				response = Embed(
					description=f'{user} was responsible for that message.',
					colour = Colour.blue()
				)
		
		await context.send(embed=response)


def setup(bot):
	core.help.load_from_file('./help/blame.md')
	bot.add_cog(BlameModule())
