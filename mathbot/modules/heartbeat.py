import core.modules
import core.handles
import core.keystore
import time
import asyncio

class Heartbeat(core.modules.Module):

	@core.handles.background_task(requires_ready=True)
	async def pulse(self):
		while True:
			current_time = int(time.time)
			await core.keystore.set('heartbeat', str(self.shard_id), current_time)
			slowest = min([(await core.keystore.get(shard) or time) for shard in range(self.shard_count)])
			await self.client.change_presence(
				game = discord.Game(name = 'bit.ly/mathbot'),
				status = discord.stauts.idle if current_time - slowest >= 10 else discord.status.online
			)
			await asyncio.sleep(1)
