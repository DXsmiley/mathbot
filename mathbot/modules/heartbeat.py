''' Module to update the status icon of the bot whever it's being restarted or something. '''

import core.module
import core.handles
import core.keystore
import time
import asyncio
from discord.ext.commands import command

class Heartbeat:

	def __init__(self, bot):
		self.bot = bot
		self.background_task = bot.loop.create_task(self.pulse())

	async def pulse(self):
		''' Repeatedly update the status of the bot '''
		tick = 0
		while not self.bot.is_closed(): # TODO: Stop the task if the cog is unloaded
			current_time = int(time.time())
			for shard in self.bot.shard_ids:
				await core.keystore.set('heartbeat', str(shard), current_time)
			tick += 1
			if tick % 5 == 0:
				# Find the slowest shard
				slowest = min([
					(await core.keystore.get('heartbeat', str(shard)) or 1)
					for shard in range(self.bot.shard_count)
				])
				await self.bot.change_presence(
					game=discord.Game(name='bit.ly/mathbot'),
					status=discord.Status.idle if current_time - slowest >= 30 else discord.Status.online
				)
			await asyncio.sleep(3)
		# Specify that the current shard is no longer running. Helps the other shards update sooner.
		for i in self.bot.shard_ids:
			await core.keystore.set('heartbeat', str(i), 1)

	@command()
	async def heartbeat(self, context):
		current_time = int(time.time())
		lines = ['```']
		for i in range(self.bot.shard_count):
			last_time = await core.keystore.get('heartbeat', str(i)) or 1
			timediff = min(60 * 60 - 1, current_time - last_time)
			lines.append('{} {:2d} - {:2d}m {:2d}s'.format(
				'>' if i in self.bot.shard_ids else ' ',
				i + 1,
				timediff // 60,
				timediff % 60
			))
		lines.append('```')
		await context.send('\n'.join(lines))

def setup(bot):
	bot.add_cog(Heartbeat(bot))
