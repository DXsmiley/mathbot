#!/usr/bin/env python3
# encoding: utf-8

import os
import sys
import warnings
import logging
import asyncio
import re
import json
import typing
import traceback

import termcolor
import discord
import discord.ext.commands
from discord.ext.commands.errors import *

import core.blame
import core.keystore
import utils


warnings.simplefilter('default')
logging.basicConfig(level = logging.INFO)


core.blame.monkey_patch()


class MathBot(discord.ext.commands.AutoShardedBot):

	def __init__(self, parameters):
		super().__init__(
			command_prefix=_determine_prefix,
			pm_help=True,
			shard_count=parameters.get('shards total'),
			shard_ids=parameters.get('shards mine')
		)
		self.parameters = parameters
		self.release = parameters.get('release')
		self.keystore = _create_keystore(parameters)
		assert self.release in ['development', 'beta', 'release']
		self.remove_command('help')
		for i in _get_extensions(parameters):
			self.load_extension(i)

	def run(self):
		super().run(self.parameters.get('token'))

	async def on_message(self, message):
		if self.release != 'production' or not message.author.is_bot:
			await self.process_commands(message)

	async def on_error(self, event, *args, **kwargs):
		print('On Error')
		print(event, *args, **kwargs)
		traceback.print_exc()

	async def on_command_error(self, context, error):
		if isinstance(error, CommandNotFound):
			return
		termcolor.cprint('An error occurred while running a command', 'red')
		termcolor.cprint(''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)), 'blue')
		embed = discord.Embed(
			title='An error occurred',
			colour=discord.Colour.red(),
			description='Yes this is a thing.'
		)
		await context.send(embed=embed)


def run(parameters):
	if sys.getrecursionlimit() < 2500:
		sys.setrecursionlimit(2500)
	MathBot(parameters).run()


@utils.listify
def _get_extensions(parameters):
	yield 'modules.about'
	yield 'modules.blame'
	# yield 'modules.calcmod'
	# yield 'modules.dice'
	# yield 'modules.greeter'
	# yield 'modules.heartbeat'
	yield 'modules.help'
	# yield 'modules.purge'
	# yield 'modules.reporter'
	# yield 'modules.settings'
	# yield 'modules.wolfram'
	if parameters.get('release') == 'development':
		yield 'modules.echo'
		# yield 'modules.throws'
	if parameters.get('release') == 'production':
		yield 'modules.analytics'


def _create_keystore(parameters):
	keystore_mode = parameters.get('keystore mode')
	if keystore_mode == 'redis':
		return core.keystore.create_redis(
			parameters.get('keystore redis url'),
			parameters.get('keystore redis number')
		)
	if keystore_mode == 'disk':
		return core.keystore.create_disk(parameters.get('keystore disk filename'))
	raise ValueError(f'"{keystore_mode}" is not a valid keystore mode')


async def _determine_prefix(bot, message):
	prefixes = [f'<@!{bot.user.id}> ', f'<@{bot.user.id}> ', '=']
	if message.guild is None:
		prefixes.append('')
	# TODO: Grab custom prefixes here
	return prefixes

if __name__ == '__main__':
	print('bot.py found that it was the main module. You should be invoking the bot from entrypoint.py')
	sys.exit(1)