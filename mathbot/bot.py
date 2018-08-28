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

from queuedict import QueueDict
from modules.reporter import report


warnings.simplefilter('default')
logging.basicConfig(level = logging.INFO)
sys.setrecursionlimit(2500)
core.blame.monkey_patch()


REQUIRED_PERMISSIONS_MESSAGE = '''\
The bot does not have all the permissions it requires in order to run in this channel. The bot may behave unexpectedly without them.
 - Add reactions
 - Attach files
 - Embed links
'''


class MathBot(discord.ext.commands.AutoShardedBot):

	def __init__(self, parameters):
		super().__init__(
			command_prefix=_determine_prefix,
			pm_help=True,
			shard_count=parameters.get('shards total'),
			shard_ids=parameters.get('shards mine'),
			max_messages=100,
			fetch_offline_members=False
		)
		self.parameters = parameters
		self.release = parameters.get('release')
		self.keystore = _create_keystore(parameters)
		self.settings = core.settings.Settings(self.keystore)
		self.command_output_map = QueueDict(timeout = 60 * 10) # 10 minute timeout
		assert self.release in ['development', 'beta', 'release']
		self.remove_command('help')
		for i in _get_extensions(parameters):
			self.load_extension(i)

	def run(self):
		super().run(self.parameters.get('token'))

	async def on_message(self, message):
		if self.release != 'production' or not message.author.bot:
			if utils.is_private(message.channel) or self._can_post_in_guild(message):
				await self.process_commands(message)

	def _can_post_in_guild(self, message):
		perms = message.channel.permissions_for(message.guild.me)
		return perms.read_messages and perms.send_messages

	# Enabling this will cause output to be deleted with the coresponding
	# commands are deleted.
	# async def on_message_delete(self, message):
	# 	to_delete = self.command_output_map.pop(message.id, [])
	# 	await self._delete_messages(to_delete)

	# Using this, it's possible to edit a tex message
	# into some other command, so I might add some additional
	# restrictions to this later.
	async def on_message_edit(self, before, after):
		to_delete = self.command_output_map.pop(before.id, [])
		if to_delete:
			await asyncio.gather(
				self._delete_messages(to_delete),
				self.on_message(after)
			)

	async def _delete_messages(self, messages):
		for i in messages:
			await i.delete()
			await asyncio.sleep(2)

	def message_link(self, invoker, sent):
		lst = self.command_output_map.get(invoker.id, default=[])
		self.command_output_map[invoker.id] = lst + [sent]

	async def on_command(self, ctx):
		perms = ctx.message.channel.permissions_for(ctx.me)
		if not all([perms.add_reactions, perms.attach_files, perms.embed_links]):
			await ctx.send(REQUIRED_PERMISSIONS_MESSAGE)

	async def on_error(self, event, *args, **kwargs):
		was_handled = False
		_, error, _ = sys.exc_info()
		if event in ['message', 'on_message']:
			was_handled = await self.report_error(args[0].channel, error)
		if event == 'on_command':
			was_handled = await self.report_error(args[0], error)
		if not was_handled:
			termcolor.cprint(f'An error occurred outside of a command and was not handled: {event}', 'red')
			termcolor.cprint(traceback.format_exc(), 'blue')

	async def on_command_error(self, context, error):
		details = f'{self.shard_ids} **Error while running command**\n```\n{context.message.clean_content}\n```'
		if not await self.report_error(context, error, details):
			termcolor.cprint('An unknown issue occurred while running a command', 'red')
			termcolor.cprint(''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__)), 'blue')
			embed = discord.Embed(
				title='An unknown error occurred.',
				colour=discord.Colour.red(),
				description='This is even worse than normal.'
			)
			await context.send(embed=embed)

	async def report_error(self, destination, error, human_details=''):
		if isinstance(error, CommandNotFound):
			pass # Ignore unfound commands
		elif isinstance(error, MissingRequiredArgument):
			await destination.send(f'Argument {error.param} required.')
		elif isinstance(error, TooManyArguments):
			await destination.send(f'Too many arguments given.')
		elif isinstance(error, BadArgument):
			await destination.send(f'Bad argument: {error}')
		elif isinstance(error, NoPrivateMessage):
			await destination.send(f'That command cannot be used in DMs.')
		elif isinstance(error, core.settings.DisabledCommandByServerOwner):
			await destination.send(embed=discord.Embed(
				title='Command disabled',
				description=f'The sever owner has disabled that command in this location.',
				colour=discord.Colour.orange()
			))
		elif isinstance(error, DisabledCommand):
			await destination.send(embed=discord.Embed(
				title='Command globally disabled',
				description=f'That command is currently disabled. Either it relates to an unreleased feature or is undergoing maintaiance.',
				colour=discord.Colour.orange()
			))
		elif isinstance(error, CommandInvokeError):
			tb = ''.join(traceback.format_exception(etype=type(error.original), value=error.original, tb=error.original.__traceback__))
			termcolor.cprint('An error occurred while running a command', 'red')
			termcolor.cprint(tb, 'blue')
			embed = discord.Embed(
				title='An internal error occurred while running the command.',
				colour=discord.Colour.red(),
				description='A report has been automatically sent to the developer. If you wish to follow up, or seek additional assistance, you may do so at the mathbot server: https://discord.gg/JbJbRZS'
			)
			await destination.send(embed=embed)
			await report(self, f'{human_details}\n```\n{tb}\n```')
		else:
			return False
		return True


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
	yield 'modules.heartbeat'
	yield 'modules.help'
	yield 'modules.latex'
	yield 'modules.purge'
	yield 'modules.reporter'
	yield 'modules.settings'
	yield 'modules.wolfram'
	if parameters.get('release') == 'development':
		yield 'modules.echo'
		yield 'modules.throws'
	# if parameters.get('release') == 'production':
	# 	yield 'modules.analytics'


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
	if message.guild is None:
		prefixes = ['= ', '=', '']
	else:
		custom = await bot.settings.get_server_prefix(message)
		prefixes = [custom + ' ', custom]
	return discord.ext.commands.when_mentioned_or(*prefixes)(bot, message)


if __name__ == '__main__':
	print('bot.py found that it was the main module. You should be invoking the bot from entrypoint.py')
	sys.exit(1)
