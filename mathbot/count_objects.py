# I swear this is like the fifth time I've programmed this.

import os
import sys
import json
import re
from mathbot import utils
from mathbot import core
from mathbot.core.parameters import Parameters
import objgraph
import discord
import discord.ext.commands
import logging
import gc


logging.basicConfig(level = logging.INFO)


class MyBot(discord.ext.commands.AutoShardedBot):

	def __init__(self, parameters: Parameters):
		super().__init__(
			command_prefix='nobodyisgonnausethis',
			pm_help=True,
			shard_count=parameters.shards.total,
			shard_ids=parameters.shards.mine,
			max_messages=2000,
			fetch_offline_members=False
		)
		self.parameters = parameters
		self.release = parameters.release
		# self.keystore = _create_keystore(parameters)
		# self.settings = core.settings.Settings(self.keystore)
		# self.command_output_map = QueueDict(timeout = 60 * 10) # 10 minute timeout
		self.remove_command('help')

	def run(self):
		super().run(self.parameters.token)


	async def on_ready(self):
		# objgraph.show_most_common_types()
		# self._connection.emoji = []
		# gc.collect()
		objgraph.show_most_common_types()



if __name__ == '__main__':

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

    MyBot(retrieve_parameters()).run()
