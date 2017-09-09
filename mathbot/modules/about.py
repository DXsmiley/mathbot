import datetime
import discord
import psutil
import os
import asyncio
import core.help
import core.module

BOT_COLOUR = 1424337

startup_time = datetime.datetime.now()


STATS_MESSAGE = """\
Servers: {}
Uptime: {} days {} hours {} minutes {} seconds
"""


core.help.load_from_file('./help/help.md', topics = [''])
core.help.load_from_file('./help/about.md')
core.help.load_from_file('./help/management.md')


class AboutModule(core.module.Module):

	# Send a message detailing the shard number, server count,
	# uptime and and memory using of this shard
	@core.handles.command('stats stat status', '')
	async def command_stats(self, message):
		embed = discord.Embed(title = 'MathBot Stats', colour = BOT_COLOUR)
		num_servers = len(self.client.servers)
		embed.add_field(name = 'Servers', value = num_servers, inline = True)
		shard_text = '{} of {}'.format(self.shard_id + 1, self.shard_count)
		embed.add_field(name = 'Shard', value = shard_text, inline = True)
		uptime = get_uptime()
		embed.add_field(name = 'Uptime', value = uptime, inline = True)
		memory = '{} MB'.format(get_memory_usage())
		embed.add_field(name = 'Memory Usage', value = memory, inline = True)
		embed.set_footer(text = 'Time is in hh:mm')
		await self.send_message(message.channel, embed = embed, blame = message.author)

	# Aliases for the help command
	@core.handles.command('about info', '')
	async def command_about(self, message):
		return core.handles.Redirect('help', 'about')

	# Sets the playing status of the bot when it starts up
	# Also send it intermittently in case it expires (is this a thing?)
	@core.handles.background_task()
	async def update_status_message(self):
		while True:
			# status = 'bit.ly/mathbot'
			status = 'bit.ly/mb-code'
			game = discord.Game(name = status)
			await self.client.change_presence(game = game)
			await asyncio.sleep(60 * 5)


def get_uptime():
	''' Returns a string representing how long the bot has been running for '''
	cur_time = datetime.datetime.now()
	up_time = cur_time - startup_time
	up_hours = up_time.seconds // (60 * 60) + (up_time.days * 24)
	up_minutes = (up_time.seconds // 60) % 60
	return '{:02d}:{:02d}'.format(up_hours, up_minutes)


def get_memory_usage():
	''' Returns the amount of memory the bot is using, in MB '''
	proc = psutil.Process(os.getpid())
	mem = proc.memory_info().rss
	return mem // (1024 * 1024)
