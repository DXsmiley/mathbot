# Usage:
#     python update_logo.py parameters.json
# 
# Will load a profile picture from logo.png


import discord
import asyncio
from mathbot import core
from mathbot import utils

@utils.apply(core.parameters.load_parameters, list)
def retrieve_parameters():
    for i in sys.argv[1:]:
        if re.fullmatch(r'\w+\.env', i):
            yield json.loads(os.environ.get(i[:-4]))
        elif i.startswith('{') and i.endswith('}'):
            yield json.loads(i)
        else:
            with open(i) as f:
                yield json.load(f)

parameters = retrive_parameters()

client = discord.Client(
    shard_id=0,
    shard_count=parameters.shards.total
)

@client.event
async def on_ready():
    print('Logged in as', client.user.name)
    with open('logo.png', 'rb') as avatar:
        await client.edit(avatar=avatar)

    print('Done updating profile picture')
    client.close()

client.run(parameters.token)
