''' Module to update the status icon of the bot whever it's being restarted or something. '''

import core.module
import core.handles
import core.keystore
import time
import asyncio
import discord

class Heartbeat(core.module.Module):

	@core.handles.background_task(requires_ready=True)
	async def pulse(self):
		''' Repeatedly update the status of the bot '''
		tick = 0
		while self.running:
			current_time = int(time.time())
			await core.keystore.set('heartbeat', str(self.shard_id), current_time)
			# Find the slowest shard
			slowest = min([
				(await core.keystore.get('heartbeat', str(shard)) or 1)
				for shard in range(self.shard_count)
			])
			tick += 1
			if tick % 5 == 0:
				await self.client.change_presence(
					game=discord.Game(name='bit.ly/mathbot'),
					status=discord.Status.idle if current_time - slowest >= 30 else discord.Status.online
				)
			await asyncio.sleep(3)
		# Specify that the current shard is no longer running. Helps the other shards update sooner.
		await core.keystore.set('heartbeat', str(self.shard_id), 1)

	@core.handles.command('heartbeat', '')
	async def heartbeat(self, message):
		current_time = int(time.time())
		lines = ['```']
		for i in range(self.shard_count):
			timediff = min(
				60 * 60 - 1,
				current_time - (await core.keystore.get('heartbeat', str(i)) or 1)
			)
			lines.append('{} {:2d} - {:2d}m {:2d}s'.format(
				'>' if i == self.shard_id else ' ',
				i + 1,
				timediff // 60,
				timediff % 60
			))
		lines.append('```')
		await self.send_message(message, '\n'.join(lines))