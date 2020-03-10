''' Module to update the status icon of the bot whever it's being restarted or something. '''

import time
import asyncio
import discord
import traceback
from discord.ext.commands import command, Cog

class Heartbeat(Cog):

	def __init__(self, bot):
		self.bot = bot
		self.background_task = None

	@Cog.listener()
	async def on_ready(self):
		if self.background_task is None:
			self.background_task = self.bot.loop.create_task(self.pulse())

	async def pulse(self):
		''' Repeatedly update the status of the bot '''
		print('Heartbeat coroutine is running')
		tick = 0
		while not self.bot.is_closed(): # TODO: Stop the task if the cog is unloaded
			current_time = int(time.time())
			for shard in self.bot.shard_ids:
				await self.bot.keystore.set('heartbeat', str(shard), current_time)
			tick += 1
			if tick % 5 == 0:
				# Find the slowest shard
				slowest = min([
					(await self.bot.keystore.get('heartbeat', str(shard)) or 1)
					for shard in range(self.bot.shard_count)
				])
				try:
					await self.bot.change_presence(
						activity=discord.Game('with numbers'),
						status=discord.Status.idle if current_time - slowest >= 30 else discord.Status.online
					)
				except:
					print('Error while changing presence based on heartbeat')
					traceback.print_exc()
			await asyncio.sleep(3)
		# Specify that the current shard is no longer running. Helps the other shards update sooner.
		for i in self.bot.shard_ids:
			await self.bot.keystore.set('heartbeat', str(i), 1)

	@command()
	async def heartbeat(self, context):
		error_queue_length = await self.bot.keystore.llen('error-report')
		current_time = int(time.time())
		lines = ['```']
		for i in range(self.bot.shard_count):
			last_time = await self.bot.keystore.get('heartbeat', str(i)) or 1
			timediff = min(60 * 60 - 1, current_time - last_time)
			lines.append('{} {:2d} - {:2d}m {:2d}s'.format(
				'>' if i in self.bot.shard_ids else ' ',
				i + 1,
				timediff // 60,
				timediff % 60
			))
		lines += ['', f'Error queue length: {error_queue_length}', '```']
		await context.send('\n'.join(lines))

def setup(bot):
	bot.add_cog(Heartbeat(bot))
