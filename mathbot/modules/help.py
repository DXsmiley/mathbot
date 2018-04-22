''' Module used to send help documents to users. '''

import re
import core.help
import core.module
import core.settings
import core.keystore


CONSTANTS = {
	'add_link': 'https://discordapp.com/oauth2/authorize?&client_id=172236682245046272&scope=bot&permissions=126016', # pylint: disable=line-too-long
	'server_link': 'https://discord.gg/JbJbRZS'
}


def doubleformat(string, **replacements):
	''' Acts a but like format, but works on things wrapped in *two* curly braces. '''
	for key, value in replacements.items():
		string = string.replace('{{' + key + '}}', value)
	return string


class HelpModule(core.module.Module):
	''' Module that serves help pages. '''

	@core.handles.command('support', '')
	async def support_command(self, msg):
		''' =support command, simply PMs the caller a link to the support server. '''
		reply = 'Official support server: https://discord.gg/JbJbRZS'
		await self.send_private_fallback(msg.author, msg.channel, reply, supress_warning=True)

	@core.handles.command('help', '*')
	async def help_command(self, msg, topic):
		''' Help command itself.
			Help is sent via DM, but a small message is also sent in the public chat.
			Specifying a non-existent topic will show an error and display a list
			of topics that the user could have meant.
		'''
		if msg.author.bot:
			return

		topic = re.sub(r' +', ' ', topic.strip())
		if topic in ['topics', 'topic', 'list']:
			return await self._send_topic_list(msg)

		found_doc = core.help.get(topic)
		if found_doc is None:
			return await self._suggest_topics(msg, topic)

		was_private = True
		for index, page in enumerate(found_doc):
			if msg.channel.is_private:
				prefix = await core.keystore.get('last-seen-prefix', msg.author.id) or '='
			else:
				prefix = await core.settings.get_server_prefix(msg.server)
				await core.keystore.set('last-seen-prefix', msg.author.id, prefix)
			page = doubleformat(
				page,
				prefix=prefix,
				mention=self.client.user.mention,
				**CONSTANTS
			)
			# await self.send_message(msg, page)
			args = [msg.author, msg.channel, page]
			if not await self.send_private_fallback(*args, supress_warning=index > 0):
				was_private = False
		if was_private and not msg.channel.is_private:
			if topic:
				reply = "Information on `{}` has been sent to you privately.".format(topic)
			else:
				reply = "Help has been sent to you privately."
			await self.send_message(msg, reply)


	async def _send_topic_list(self, msg):
		listing = ' - `' + '`\n - `'.join(core.help.listing()) + '`\n'
		reply = 'The following help topics exist:\n{}'.format(listing)
		# await self.send_message(msg, reply)
		args = [msg.author, msg.channel, reply]
		if await self.send_private_fallback(*args) and not msg.channel.is_private:
			await self.send_message(msg, 'A list of help topics has been sent to you privately.')


	async def _suggest_topics(self, msg, topic):
		suggestions = core.help.get_similar(topic)
		if not suggestions:
			reply = "Help topic `{}` does not exist.".format(topic)
		elif len(suggestions) == 1:
			reply = "Help topic `{}` does not exist.\nMaybe you meant `{}`?".format(topic, suggestions[0])
		else:
			reply = "Help topic `{}` does not exist.\nMaybe you meant one of: {}?".format(
				topic,
				', '.join(map("`{}`".format, suggestions))
			)
		await self.send_message(msg, reply)
