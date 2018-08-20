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
import core.settings
import utils


warnings.simplefilter('default')
logging.basicConfig(level = logging.INFO)
sys.setrecursionlimit(2500)
core.blame.monkey_patch()


class MathBot(discord.ext.commands.AutoShardedBot):

	def __init__(self, parameters):
		super().__init__(
			command_prefix=_determine_prefix,
			pm_help=True,
			shard_count=parameters.get('shards total'),
			shard_ids=parameters.get('shards mine'),
			max_messages=100
		)
		self.parameters = parameters
		self.release = parameters.get('release')
		self.keystore = _create_keystore(parameters)
		self.settings = core.settings.Settings(self.keystore)
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
		termcolor.cprint('An error occurred outside of a command', 'red')
		termcolor.cprint(traceback.format_exc(), 'blue')

	async def on_command_error(self, context, error):
		if isinstance(error, CommandNotFound):
			return
		elif isinstance(error, MissingRequiredArgument):
			await context.send(f'Argument {error.param} required.')
		elif isinstance(error, TooManyArguments):
			await context.send(f'Too many arguments given.')
		elif isinstance(error, NoPrivateMessage):
			await context.send(f'That command cannot be used in DMs.')
		elif isinstance(error, core.settings.DisabledCommandByServerOwner):
			await context.send(embed=discord.Embed(
				title='Command disabled',
				description=f'The sever owner has disabled that command in this location.',
				colour=discord.Colour.orange()
			))
		elif isinstance(error, DisabledCommand):
			await context.send(embed=discord.Embed(
				title='Command globally disabled',
				description=f'That command is currently disabled. Either it relates to an unreleased feature or is undergoing maintaiance.',
				colour=discord.Colour.orange()
			))
		elif isinstance(error, CommandInvokeError):
			termcolor.cprint('An error occurred while running a command', 'red')
			termcolor.cprint(''.join(traceback.format_exception(etype=type(error.original), value=error.original, tb=error.original.__traceback__)), 'blue')
			embed = discord.Embed(
				title='An internal error occurred while running the command.',
				colour=discord.Colour.red(),
				description='Automatic reporting is currently disabled.'
			)
			await context.send(embed=embed)
		else:
			termcolor.cprint('An unknown issue occurred while running a command', 'red')
			termcolor.cprint(''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)), 'blue')
			embed = discord.Embed(
				title='An unknown error occurred.',
				colour=discord.Colour.red(),
				description='This is even worse than normal.'
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
	yield 'modules.calcmod'
	yield 'modules.dice'
	# yield 'modules.greeter'
	# yield 'modules.heartbeat'
	yield 'modules.help'
	yield 'modules.latex'
	# yield 'modules.purge'
	# yield 'modules.reporter'
	yield 'modules.settings'
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
