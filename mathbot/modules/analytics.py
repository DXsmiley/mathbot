# Provides stats on the bot to bot listing services

import aiohttp

import core.module
import core.handles
import core.parameters

CARBON_URL = 'https://www.carbonitex.net/discord/data/botdata.php'
DISCORD_BOTS_URL = 'https://bots.discord.pw/api/bots/{bot_id}/stats'

class AnalyticsModule(core.module.Module):

	@core.handles.startup_task()
	async def identify_bot_farms(self):
		''' This function lists any medium / large servers with more bots
			than humans. The eventual goal is to identify and leave any
			servers that are just full of bots and don't actually have any
			proper activity in them. I should also add some metric gathering
			to figure out how much the bot gets used in various servers.
		'''
		print('    Humans |  Bots | Server Name')
		for server in self.client.servers:
			num_humans = 0
			num_bots = 0
			for user in server.members:
				if user.bot:
					num_bots += 1
				else:
					num_humans += 1
			num_members = num_humans + num_bots
			if num_bots > num_humans and num_members > 20:
				print('    {:6d} | {:5d} | {}'.format(
					num_humans,
					num_bots,
					server.name
				))

	@core.handles.startup_task()
	async def post_stats(self):
		ns = self.num_servers()
		print('Shard', self.shard_id, 'is on', ns, 'servers')
		async with aiohttp.ClientSession() as session:
			# Submit stats to carbonitex.net
			carbon_key = core.parameters.get('analytics carbon')
			if carbon_key:
				data = {
					'key': carbon_key,
					'servercount': ns
				}
				async with session.post(CARBON_URL, data = data) as response:
					print('Analytics: Carbon:', response.status)
			# Submit stats to bots.discord.pw
			discord_bots_key = core.parameters.get('analytics discord-bots')
			if discord_bots_key:
				url = DISCORD_BOTS_URL.format(bot_id = self.client.user.id)
				payload = {
					'json': {
						'server_count': ns,
						'shard_id': self.shard_id,
						'shard_count': self.shard_count
					},
					'headers': {
						'Authorization': discord_bots_key
					}
				}
				async with session.post(url, **payload) as response:
					print('Analytics: bots.pw:', response.status)

	def num_servers(self):
		# return '3800' # Something temporary (but accurate-ish) while I'm testing.
		return len(self.client.servers)
