import collections
import asyncio
import traceback
import discord

import core.module
import core.handles
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


class ReporterModule(core.module.Module):

	@core.handles.background_task(requires_ready = True)
	async def queue_reports(self):
		try:
			while self.running:
				if len(QUEUE) > 0:
					item = QUEUE.pop()
					await core.keystore.lpush('error-report', item)
				else:
					await asyncio.sleep(5)
		except asyncio.CancelledError:
			raise
		except Exception:
			print('Exception in ReporterModule.queue_reports on shard {}. This is bad.'.format(self.client.shard_id))

	@core.handles.background_task(requires_ready = True)
	async def send_reports(self):
		try:
			report_channel = await self.get_report_channel()
			if report_channel:
				print('Shard', self.client.shard_id, 'will report errors!')
				print('Channel:', report_channel)
				while self.running:
					message = await core.keystore.rpop('error-report')
					if message is not None:
						# Errors should have already been trimmed before they reach this point,
						# but this is just in case something slips past
						if len(message) > 1900:
							message = message[1900:] + ' **(emergency trim)**'
						await self.client.send_message(report_channel, message)
					else:
						await asyncio.sleep(5)
		except asyncio.CancelledError:
			raise
		except Exception:
			print('Exception in ReporterModule.send_reports on shard {}. This is bad.'.format(self.client.shard_id))
			traceback.print_exc()

	async def get_report_channel(self) -> typing.Optional[discord.Channel]:
		channel_id = core.parameters.get('error-reporting channel')
		if channel_id:
			try:
				channel = self.client.get_channel(channel_id)
				if channel:
					await self.client.send_message(channel, 'Shard {} reporting for duty!'.format(self.shard_id))
					return channel
			except Exception:
				pass
		return None

def enque(string: str):
	QUEUE.appendleft(string)
