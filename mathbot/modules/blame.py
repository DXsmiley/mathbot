# Used to keep track of who was responsible for causing the bot to send
# a particular message. This exists because people can use the =tex
# command then delete their message to get the bot to say offensive or
# innapropriate things. This allows server moderators (or anyone else really)
# to track down the person responsible

import core.help
from core.util import respond
from discord.ext.commands import Cog, Context
from discord import Embed, Colour
from discord.ext.commands.hybrid import hybrid_command


class BlameModule(Cog):

	@hybrid_command()
	@respond
	async def blame(self, context: Context, message_id: str):
		if message_id == 'recent':
			async for m in context.channel.history(limit=100):
				if m.author == context.bot.user:
					user = await context.bot.keystore.get_json('blame', str(m.id))
					if user is not None:
						return found_response(user, 'was responsible for the most recent message in this channel.')
			return error_response('Could not find any recent message')
		elif message_id.isnumeric():
			user = await context.bot.keystore.get_json('blame', message_id)
			if user is None:
				return error_response('Could not find the blame information for that message')
			return found_response(user, 'was responsible for that message.')
		return error_response('Argument was not a valid message ID')			


def found_response(blob, description):
	user = '{mention} ({name}#{discriminator})'.format(**blob)
	return Embed(description=f'{user} {description}', colour=Colour.blue())


def error_response(text):
	return Embed(description=text, colour=Colour.red())


def setup(bot):
	core.help.load_from_file('./help/blame.md')
	return bot.add_cog(BlameModule())
