import collections
import asyncio
import traceback
import discord
from discord.ext.commands import Cog
import termcolor

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


class ReporterModule(Cog):

	def __init__(self, bot):
		self.bot = bot
		self.task = None

	@Cog.listener()
	async def on_ready(self):
		if self.task is not None:
			self.task.end()
		self.task = ReporterTask(self.bot)


class ReporterTask:

	def __init__(self, bot):
		self.bot = bot
		self.should_end = False
		self.bot.loop.create_task(self.send_reports())

	def end(self):
		self.should_end = True

	async def send_reports(self):
		print('Shard', self.bot.shard_ids, 'started reporting task.')
		await asyncio.sleep(10)
		try:
			report_channel = await self.get_report_channel()
			if report_channel is None:
				message = f'Shard {self.bot.shard_ids} has started'
				print(message)
				await report(self.bot, message)
				return
			termcolor.cprint(f'Shard `{self.bot.shard_ids}` will report errors', 'green')
			await report_channel.send(f'Shard `{self.bot.shard_ids}` reporting for duty!')
			while not self.should_end:
				try:
					message = await self.bot.keystore.rpop('error-report')
					if message:
						# Errors should have already been trimmed before they reach this point,
						# but this is just in case something slips past
						termcolor.cprint('Sending error report', 'yellow')
						termcolor.cprint(message, 'yellow')
						termcolor.cprint('--------------------', 'yellow')
						if len(message) > 1900:
							message = message[:1900] + ' **(emergency trim)**'
						await report_channel.send(message)
					else:
						await asyncio.sleep(10)
				except asyncio.CancelledError:
					raise
				except Exception:
					m = f'Exception in ReporterModule.send_reports on shard {self.bot.shard_id}. This is bad.'
					termcolor.cprint('*' * len(m), 'red')
					termcolor.cprint(m, 'red')
					termcolor.cprint('*' * len(m), 'red')
					traceback.print_exc()
			print('Report sending task has finished')
		except Exception:
			m = f'Exception in ReporterModule.send_reports on shard {self.bot.shard_id} has killed the task.'
			termcolor.cprint('*' * len(m), 'red')
			termcolor.cprint(m, 'red')
			termcolor.cprint('*' * len(m), 'red')
			traceback.print_exc()

	async def get_report_channel(self) -> typing.Optional[discord.TextChannel]:
		channel_id = self.bot.parameters.get('error-reporting channel')
		if channel_id:
			try:
				return self.bot.get_channel(channel_id)
			except Exception:
				pass


async def report(bot, string: str):
	await bot.keystore.lpush('error-report', string)


def setup(bot):
	bot.add_cog(ReporterModule(bot))
