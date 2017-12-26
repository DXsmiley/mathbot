import re
import core.help
import core.module
import core.settings
import core.keystore
import discord
import itertools


CONSTANTS = {
	'add_link': 'https://discordapp.com/oauth2/authorize?&client_id=172236682245046272&scope=bot&permissions=126016',
	'server_link': 'https://discord.gg/JbJbRZS'
}


def doubleformat(string, **replacements):
	for key, value in replacements.items():
		string = string.replace('{{' + key + '}}', value)
	return string


class HelpModule(core.module.Module):

	@core.handles.command('help', '*')
	async def help_command(self, message, topic):
		topic = re.sub(r' +', ' ', topic.strip())
		if topic in ['topics', 'topic', 'list']:
			listing = ' - `' + '`\n - `'.join(core.help.listing()) + '`\n'
			msg = 'The following help topics exist:\n{}'.format(listing)
			# await self.send_message(message.channel, msg, blame = message.author)
			if await self.send_private_fallback(message.author, message.channel, msg):
				await self.send_message(message.channel, 'A list of help topics sent to you privately.', blame = message.author)
		else:
			response = core.help.get(topic)
			if response is not None:
				was_private = True
				for index, page in enumerate(response):
					if message.channel.is_private:
						prefix = await core.keystore.get('last-seen-prefix', message.author.id) or '='
					else:
						prefix = await core.settings.get_server_prefix(message.server.id)
						await core.keystore.set('last-seen-prefix', message.author.id, prefix)
					page = doubleformat(
						page,
						prefix = prefix,
						mention = self.client.user.mention,
						**CONSTANTS
					)
					# await self.send_message(message.channel, page, blame = message.author)
					if not await self.send_private_fallback(message.author, message.channel, page, supress_warning = index > 0):
						was_private = False
				if was_private and not message.channel.is_private:
					if topic:
						m = "Information on '{}' has been send to you privately.".format(topic)
					else:
						m = "Help has been sent to you privately."	
					await self.send_message(message.channel, m, blame = message.author)
			else:
				msg = "Help topic '{}' does not exist.".format(topic)
				await self.send_message(message.channel, msg, blame = message.author)
