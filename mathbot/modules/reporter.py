import collections
import asyncio

import core.module
import core.handles
import core.keystore


# This queue is a global object, which actually means that multiple
# shards might fiddle with it. HOWEVER, this is fine since there'll
# just be multiple shards pushing from the queue to the redis store
# every 10 seconds or so. Because we're using coroutines and not
# read threads, this is OK.
QUEUE = collections.deque()


class ReporterModule(core.module.Module):

	@core.handles.background_task(requires_ready = True)
	async def queue_reports(self):
		while True:
			if len(QUEUE) > 0:
				item = QUEUE.pop()
				await core.keystore.lpush('error-report', item)
			else:
				await asyncio.sleep(10)

	@core.handles.background_task(requires_ready = True)
	async def send_reports(self):
		report_channel = await self.get_report_channel()
		if report_channel:
			print('Shard', self.client.shard_id, 'will report errors!')
			while True:
				message = await core.keystore.rpop('error-report')
				if message is not None:
					await self.client.send_message(report_channel, message)
				else:
					await asyncio.sleep(10)

	async def get_report_channel(self):
		channel_id = core.parameters.get('error-reporting channel')
		if channel_id:
			try:
				channel = self.client.get_channel(channel_id)
				await self.client.send_message(channel, 'Shard {} reporting for duty!'.format(self.shard_id))
				return channel
			except Exception:
				pass
		return None

def enque(string):
	QUEUE.appendleft(string)