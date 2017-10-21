# Usage:
#     python update_logo.py parameters.json
# 
# Will load a profile picture from logo.png


import discord
import asyncio
import core.parameters

client = discord.Client(
	shard_id = 0,
	shard_count = core.parameters.get('shards total')
)

@client.event
async def on_ready():
	print('Logged in as', client.user.name)
	await client.edit_profile(
		avatar = open('logo.png', 'rb').read()
	)
	print('Done updating profile picture')
	client.close()

client.run(core.parameters.get('token'))
