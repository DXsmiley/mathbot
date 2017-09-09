import core.handles
import core.module
import core.help
import discord
import asyncio

USER_PERM_ERROR = '''\
You do not have the permissions required to perform that operation in this channel.
You need to have permission to *manage messages*.
'''

BOT_PERM_ERROR = '''\
I do not have the permissions required to perform that operation in this channel.
I need to be able to *manage messages* before Discord will allow me to run the operation.
'''

PRIVATE_ERROR = '''\
The `=purge` command cannot be used in a private channel.
See `=help purge` for more details.
'''

core.help.load_from_file('./help/purge.md')

def is_admin_message(m, prevent_global_elevation = False):
	if m.channel.is_private:
		return True
	# if m.author.id in GLOBAL_ELEVATION and not prevent_global_elevation:
	# 	return True
	perms = m.channel.permissions_for(m.author)
	return perms.manage_messages or perms.administrator

class PurgeModule(core.module.Module):

	@core.handles.command('purge', 'integer')
	async def command_purge(self, message, number):
		if message.channel.is_private:
			await self.send_message(message.channel, PRIVATE_ERROR, blame = message.author)
		elif not is_admin_message(message):
			await self.send_message(message.channel, USER_PERM_ERROR, blame = message.author)
		elif number < 1:
			await self.send_message(message.channel, 'Cannot purge less than 1 message.', blame = message.author)
		else:
			number = min(500, number)
			try:
				m = 'Purging bot results from the previous {} messages.'.format(number)
				await self.send_message(message.channel, m, blame = message.author)
				await asyncio.sleep(3)
				await self.client.purge_from(
					message.channel,
					limit = number + 1,
					check = lambda x : x.author == self.client.user
				)
				await asyncio.sleep(3)
				try:
					await self.client.delete_message(message)
					await self.send_message(message.author, 'Purge complete.', blame = message.author)
				except discord.errors.Forbidden:
					pass
			except discord.errors.Forbidden:
				await self.send_message(message.channel, BOT_PERM_ERROR, blame = message.author)
