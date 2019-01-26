# Provides stats on the bot to bot listing services

import aiohttp

BOTS_ORG_URL = 'https://discordbots.org/api/bots/{bot_id}/stats'
BOTS_GG_URL = 'https://discord.bots.gg/api/v1/bots/{bot_id}/stats'

HITLIST = [
	(BOTS_ORG_URL, 'bots-org', 'server_count', 'shard_count', 'shard_id'),
	(BOTS_GG_URL, 'bots-gg', 'guildCount', 'shardCount', 'shardId')
]

class AnalyticsModule:

	def __init__(self, bot):
		self.bot = bot

	async def identify_bot_farms(self):
		''' This function lists any medium / large servers with more bots
			than humans. The eventual goal is to identify and leave any
			servers that are just full of bots and don't actually have any
			proper activity in them. I should also add some metric gathering
			to figure out how much the bot gets used in various servers.
		'''
		print('    Humans |  Bots | Server Name')
		for server in self.bot.guilds:
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

	async def on_ready(self):
		num_servers = len(self.bot.guilds)
		num_shards = self.bot.parameters.get('shards total')
		print('Shards', self.bot.shard_ids, 'are on', num_servers, 'servers')
		async with aiohttp.ClientSession() as session:
			for shard_id in self.bot.shard_ids:
				for (url_template, key_location, k_servers, k_shard, k_sid) in HITLIST:
					key = self.bot.parameters.get('analytics ' + key_location)
					if key:
						url = url_template.format(bot_id = self.bot.user.id)
						payload = {
							'json': {
								k_servers: num_servers,
								k_shard: num_shards,
								k_sid: shard_id
							},
							'headers': {
								'Authorization': key,
								'Content-Type': 'application/json'
							}
						}
						async with session.post(url, **payload) as response:
							print(f'Analytics ({url}): {response.status}')
							if response.status not in [200, 204]:
								print(await response.text())
				num_servers = 1


def setup(bot):
	bot.add_cog(AnalyticsModule(bot))
