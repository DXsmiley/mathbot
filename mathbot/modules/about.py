import datetime
import discord
import psutil
import os
import asyncio
import aiohttp
import datetime
import core.help
import core.module
import core.dreport
import codecs


BOT_COLOUR = 0x19BAE5

startup_time = datetime.datetime.now()


STATS_MESSAGE = """\
Servers: {}
Uptime: {} days {} hours {} minutes {} seconds
"""


core.help.load_from_file('./help/help.md', topics = [''])
core.help.load_from_file('./help/about.md')
core.help.load_from_file('./help/management.md')
core.help.load_from_file('./help/commands.md')


async def get_bot_total_servers(id):
	async with aiohttp.ClientSession() as session:
		url = 'https://discordbots.org/api/bots/{}/stats'.format(id)
		async with session.get(url) as response:
			jdata = await response.json()
			return jdata.get('server_count')


class AboutModule(core.module.Module):

	# Send a message detailing the shard number, server count,
	# uptime and and memory using of this shard
	@core.handles.command('stats stat status', '')
	async def command_stats(self, message):
		embed = discord.Embed(title = 'MathBot Stats', colour = BOT_COLOUR)
		embed.add_field(
			name = 'Total Servers',
			# MathBot's ID, hard coded for proper testing.
			value = await get_bot_total_servers('134073775925886976'),
			inline = True
		)
		embed.add_field(
			name = 'Shard Servers',
			value = len(self.client.servers),
			inline = True
		)
		embed.add_field(
			name = 'Shard ID',
			value = '{} of {}'.format(self.shard_id + 1, self.shard_count),
			inline = True
		)
		embed.add_field(
			name = 'Uptime',
			value = get_uptime(),
			inline = True
		)
		embed.add_field(
			name = 'Memory Usage',
			value = '{} MB'.format(get_memory_usage()),
			inline = True
		)
		embed.set_footer(text = 'Time is in hh:mm')
		await self.send_message(message.channel, embed = embed, blame = message.author)

	@core.handles.command('ping', '')
	async def pong(self, message):
		await self.send_message(message.channel, 'Pong!', blame = message.author)

	# Aliases for the help command
	@core.handles.command('about info', '')
	async def command_about(self, message):
		return core.handles.Redirect('help', 'about')

	@core.handles.command(codecs.encode('shefhvg', 'rot_13'), '')
	async def ignore_pls(self, message):
		with open('not_an_image', 'rb') as f:
			await self.send_file(message.channel, f, filename='youaskedforit.png')
		await core.dreport.custom_report(self.client, 'It happened.')


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
