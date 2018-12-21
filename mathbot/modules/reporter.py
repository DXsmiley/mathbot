import collections
import asyncio
import traceback
import discord

import core.keystore
import core.parameters

import typing


# This queue is a global object, which actually means that multiple
# shards might fiddle with it. HOWEVER, this is fine since there'll
# just be multiple shards pushing from the queue to the redis store
# every 10 seconds or so. Because we're using coroutines and not
# real threads, this is OK.
QUEUE = typing.Deque[str]()
QUEUE = collections.deque()


class ReporterModule:

	def __init__(self, bot):
		self.bot = bot
		self.send_task = None

	async def on_ready(self):
		self.send_task = self.bot.loop.create_task(self.send_reports())
		self.sent_duty_note = False

	async def send_reports(self):
		print('Shard', self.bot.shard_ids, 'will report errors!')
		while not self.bot.is_closed():
			try:
				report_channel = await self.get_report_channel()
				message = None
				if report_channel:
					message = await self.bot.keystore.rpop('error-report')
				if message:
					# Errors should have already been trimmed before they reach this point,
					# but this is just in case something slips past
					print('Sending error report')
					print(message)
					print('--------------------')
					if len(message) > 1900:
						message = message[1900:] + ' **(emergency trim)**'
					await report_channel.send(message)
				else:
					await asyncio.sleep(10)
			except asyncio.CancelledError:
				raise
			except Exception:
				print('Exception in ReporterModule.send_reports on shard {}. This is bad.'.format(self.bot.shard_id))
				traceback.print_exc()

	async def get_report_channel(self) -> typing.Optional[discord.TextChannel]:
		channel_id = self.bot.parameters.get('error-reporting channel')
		if channel_id:
			try:
				channel = self.bot.get_channel(channel_id)
				if channel:
					if not self.sent_duty_note:
						self.sent_duty_note = True
						await channel.send('Shard `{}` reporting for duty!'.format(self.bot.shard_ids))
					return channel
			except Exception:
				pass
		return None

async def report(bot, string: str):
	await bot.keystore.lpush('error-report', string)

def setup(bot):
	bot.add_cog(ReporterModule(bot))
