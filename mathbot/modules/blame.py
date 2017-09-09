# Used to keep track of who was responsible for causing the bot to send
# a particular message. This exists because people can use the =tex
# command then delete their message to get the bot to say offensive or
# innapropriate things. This allows server moderators (or anyone else really)
# to track down the person responsible

import core.keystore
import core.module
import core.handles
import core.help

core.help.load_from_file('./help/blame.md')

MESSAGE_NOT_FOUND = "Couldn't find who was resposible for that :confused:"

MESSAGE_INVALID_ID = "That doesn't look like a valid message ID :thinking:"

MESSAGE_BLAME = '{} was responsible for that message.'


def is_message_id(s):
	return s.isnumeric()


class BlameModule(core.module.Module):

	@core.handles.command('blame', 'string')
	async def command_blame(self, message, mid):
		response = MESSAGE_INVALID_ID
		if is_message_id(mid):
			user = await core.keystore.get('blame', mid)
			response = MESSAGE_NOT_FOUND
			if user is not None:
				response = MESSAGE_BLAME.format(user)
		await self.send_private_fallback(message.author, message.channel, response, blame = message.author)
