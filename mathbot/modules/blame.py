# Used to keep track of who was responsible for causing the bot to send
# a particular message. This exists because people can use the =tex
# command then delete their message to get the bot to say offensive or
# innapropriate things. This allows server moderators (or anyone else really)
# to track down the person responsible

import core.help
from discord.ext.commands import command


MESSAGE_NOTHING_RECENT_FOUND = "No recent message was found."
MESSAGE_NOT_FOUND = "Couldn't find who was resposible for that :confused:"
MESSAGE_INVALID_ID = "`{}` is not a valid message ID"
MESSAGE_BLAME = '{} was responsible for that message.'


def is_message_id(s):
	return s.isnumeric()


class BlameModule:

	def __init__(self, bot):
		self.bot = bot

	@command()
	async def blame(self, context, message_id: str):
		response = MESSAGE_INVALID_ID.format(message_id)
		if message_id == 'recent':
			response = MESSAGE_NOTHING_RECENT_FOUND
			async for m in self.client.logs_from(message.channel, limit=50):
				if m.author == self.bot.user:
					user = await bot.keystore.get('blame', m.id)
					if user is not None:
						response = MESSAGE_BLAME.format(user)
		elif is_message_id(message_id):
			user = await core.keystore.get('blame', message_id)
			response = MESSAGE_NOT_FOUND if user is None else MESSAGE_BLAME.format(user)
		await context.send(response)
		# await context.author.send(response)


def setup(bot):
	core.help.load_from_file('./help/blame.md')
	bot.add_cog(BlameModule(bot))
