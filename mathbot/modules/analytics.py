# Provides stats on the bot to bot listing services

import aiohttp

CARBON_URL = 'https://www.carbonitex.net/discord/data/botdata.php'
DISCORD_BOTS_URL = 'https://bots.discord.pw/api/bots/{bot_id}/stats'
BOTS_ORG_URL = 'https://discordbots.org/api/bots/{bot_id}/stats'

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
				# Submit stats to bots.discord.pw
				discord_bots_key = self.bot.parameters.get('analytics discord-bots')
				if discord_bots_key:
					url = DISCORD_BOTS_URL.format(bot_id = self.bot.user.id)
					await self.send_stats(session, num_servers, num_shards, shard_id, url, discord_bots_key)
				# Submit to discordbots.org
				bots_org_key = self.bot.parameters.get('analytics bots-org')
				if bots_org_key:
					url = BOTS_ORG_URL.format(bot_id = self.bot.user.id)
					await self.send_stats(session, num_servers, num_shards, shard_id, url, bots_org_key)
				# All servers get attached to the first shard, subsequent ones are zero
				# bots.discord.pw bugs out when given zero servers though.
				num_servers = 1

	@staticmethod
	async def send_stats(session, num_servers, num_shards, shard_id, url, key):
		# Both the servers have a similar API so we can do this
		payload = {
			'json': {
				'server_count': num_servers,
				'shard_count': num_shards,
				'shard_id': shard_id
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


def setup(bot):
	bot.add_cog(AnalyticsModule(bot))
