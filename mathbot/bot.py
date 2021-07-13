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
import objgraph
import gc
import time

import termcolor
import discord
import discord.ext.commands
from discord.ext.commands.errors import *

import core.blame
import core.keystore
import core.settings
import utils

from queuedict import QueueDict
from modules.reporter import report, report_via_webhook_only

from advertising import AdvertisingMixin
from patrons import PatronageMixin

sys.setrecursionlimit(2500)


REQUIRED_PERMISSIONS_MESSAGE = '''\
The bot does not have all the permissions it requires in order to run in this channel. It requires the following permissions:
 - Add reactions
 - Attach files
 - Embed links
 - Read message history

Contact your server administrators to rectify this problem.
You can seek additional support on the official mathbot server: https://discord.gg/JbJbRZS
'''


class MathBot(AdvertisingMixin, PatronageMixin, discord.ext.commands.AutoShardedBot):

	def __init__(self, parameters):
		shard_count = parameters.get('shards total')
		shard_ids = parameters.get('shards mine')
		print(f'Starting bot shards {shard_ids} ({shard_count} total)')
		super().__init__(
			command_prefix=_determine_prefix,
			pm_help=True,
			shard_count=shard_count,
			shard_ids=shard_ids,
			max_messages=2000,
			fetch_offline_members=False
		)
		self.parameters = parameters
		self.release = parameters.get('release')
		self.keystore = _create_keystore(parameters)
		self.settings = core.settings.Settings(self.keystore)
		self.command_output_map = QueueDict(timeout = 60 * 10) # 10 minute timeout
		self.blocked_users = parameters.get('blocked-users')
		self.closing_due_to_indeterminite_prefix = False
		assert self.release in ['development', 'beta', 'release']
		self.remove_command('help')
		for i in _get_extensions(parameters):
			self.load_extension(i)

	def run(self):
		super().run(self.parameters.get('token'))

	async def on_shard_ready(self, shard_id):
		print('on_shard_ready', shard_id)

	async def on_ready(self):
		print('on_ready')
		self._connection.emoji = []
		gc.collect()
		objgraph.show_most_common_types()
		# await self.leave_inactive_servers()

	async def on_disconnect(self):
		print('on_disconnect')

	async def on_resumed(self):
		print('on_resumed')

	async def leave_inactive_servers(self):
		''' There's definitely something wrong with this
			Or at least, at one point it was suprting "leaving guild None",
			so it's definitely not fault tolerent enough
		'''
		threshhold = time.time() - (60 * 60 * 24 * 30 * 7) # Approx. 7 months
		for guild in self.guilds:
			try:
				should_leave = True
				for channel in guild.text_channels:
					try:
						async for message in channel.history(limit=4):
							if message.created_at.timestamp() > threshhold:
								should_leave = False
								break
					except (discord.errors.NotFound, discord.errors.Forbidden):
						pass
					if not should_leave:
						break
				if should_leave:
					print(f'Leaving guild {guild.name}')
					await guild.leave()
					await report(self, f'Leaving guild: {guild.name}')
				# else:
				# 	print(f'Staying in {guild.name}')
			except discord.errors.HTTPException:
				print(f'HTTPException while getting activity for guild: {guild.name}')

	def should_respond_to_message(self, message):
		if self.release == 'release' and message.author.bot:
			return False
		if message.author.id in self.blocked_users:
			return False
		if utils.is_private(message.channel):
			return True
		return self._can_post_in_guild(message)

	async def on_message(self, message):
		if self.should_respond_to_message(message):
			context = await self.get_context(message)
			perms = context.message.channel.permissions_for(context.me)
			required = [
				perms.add_reactions,
				perms.attach_files,
				perms.embed_links,
				perms.read_message_history,
			]
			if not context.valid:
				# dispatch a custom event
				self.dispatch('message_discarded', message)
			elif not all(required):
				await message.channel.send(REQUIRED_PERMISSIONS_MESSAGE)
			else:
				# Use d.py to invoke the actual command handler
				context.send = self.send_patch(message, context.send)
				await self.invoke(context)

	def send_patch(self, invoker, original):
		async def send(*args, **kwargs):
			sent = await original(*args, **kwargs)
			await core.blame.set_blame(self.keystore, sent, invoker.author)
			self.message_link(invoker, sent)
			return sent
		return send


	def dump_members(self, d):
		print({k: v.name for k, v in d.items()})


	def _can_post_in_guild(self, message):
		# return True # TODO: Fix this
		if message.channel is None:
			return False
		# print('==== stuff ====')
		# print(message.guild)
		# print(message.guild.me)
		# self.dump_members(message.guild._members_cache)
		# self.dump_members(message.guild._important_members)
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
		if before.content != after.content:
			to_delete = self.command_output_map.pop(before.id, [])
			await asyncio.gather(
				self._delete_messages(to_delete),
				self.on_message(after)
			)

	async def _delete_messages(self, messages):
		for i in messages:
			try:
				await i.delete()
			except (discord.errors.Forbidden, discord.errors.NotFound):
				pass
			await asyncio.sleep(2)

	def message_link(self, invoker, sent):
		lst = self.command_output_map.get(invoker.id, default=[])
		self.command_output_map[invoker.id] = lst + [sent]

	async def on_error(self, event, *args, **kwargs):
		_, error, _ = sys.exc_info()
		if event in ['message', 'on_message', 'message_discarded', 'on_message_discarded', 'on_command_error']:
			msg = f'**Error while handling a message**'
			await self.handle_contextual_error(args[0].channel, error, msg)
		else:
			termcolor.cprint(traceback.format_exc(), 'blue')
			await self.report_error(None, error, f'An error occurred during and event and was not reported: {event}')

	async def on_command_error(self, context, error):
		details = f'**Error while running command**\n```\n{context.message.clean_content}\n```'
		await self.handle_contextual_error(context, error, details)

	async def handle_contextual_error(self, destination, error, human_details=''):
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
		elif isinstance(error, MissingPermissions):
			await destination.send(f'You are missing the following permissions required to run the command: {", ".join(error.missing_perms)}.')
		elif isinstance(error, core.settings.DisabledCommandByServerOwner):
			await destination.send(embed=discord.Embed(
				title='Command disabled',
				description=f'The server owner has disabled that command in this location.',
				colour=discord.Colour.orange()
			))
		elif isinstance(error, core.settings.DisabledCommandByServerOwnerSilent):
			pass
		elif isinstance(error, DisabledCommand):
			await destination.send(embed=discord.Embed(
				title='Command globally disabled',
				description=f'That command is currently disabled. Either it relates to an unreleased feature or is undergoing maintenance.',
				colour=discord.Colour.orange()
			))
		elif isinstance(error, CommandInvokeError):
			await self.report_error(destination, error.original, human_details)
		else:
			await self.report_error(destination, error, human_details)

	async def report_error(self, destination, error, human_details):
		tb = ''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))
		termcolor.cprint(human_details, 'red')
		termcolor.cprint(tb, 'blue')
		try:
			if destination is not None:
				embed = discord.Embed(
					title='An internal error occurred.',
					colour=discord.Colour.red(),
					description='If this keeps happening, you should contact the developers on the official mathbot server: https://discord.gg/JbJbRZS'
				)
				await destination.send(embed=embed)
		finally:
			await report(self, f'{self.shard_ids} {human_details}\n```\n{tb}\n```')


def run(parameters):
	if sys.getrecursionlimit() < 2500:
		sys.setrecursionlimit(2500)
	shards_total = parameters.get('shards total')
	shards_mine = parameters.get('shards mine')
	print(f'Running shards {shards_mine} (total {shards_total})')
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
	yield 'modules.reboot'
	yield 'modules.oeis'
	if parameters.get('release') == 'development':
		yield 'modules.echo'
		yield 'modules.throws'
	yield 'patrons' # This is a little weird.
	if parameters.get('release') == 'release':
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


# Need to do this since discord.py doesn't like iterables in here
# \uE000 is a unicode character reserved for private use
NO_VALID_PREFIXES = ['\uE000no-valid-prefixes']


async def _determine_prefix(bot, message):
	if bot.closing_due_to_indeterminite_prefix:
		return NO_VALID_PREFIXES
	try:
		if message.guild is None:
			prefixes = ['= ', '=', '']
		else:
			custom = str(await bot.settings.get_server_prefix(message))
			prefixes = [custom + ' ', custom]
		return discord.ext.commands.when_mentioned_or(*prefixes)(bot, message)
	except Exception:
		# Avoid a flood of error messages.
		if not bot.closing_due_to_indeterminite_prefix:
			m = f'Exception occurred while determining prefixes, shutting down bot (shards `{bot.shard_ids}`)'
			termcolor.cprint('*' * len(m), 'red')
			termcolor.cprint(m, 'red')
			termcolor.cprint('*' * len(m), 'red')
			traceback.print_exc()
			# Only report errors via the webhook since the redis server
			# might be unavailable at this point
			bot.closing_due_to_indeterminite_prefix = True
			await report_via_webhook_only(bot, m)
			await bot.close()
		return NO_VALID_PREFIXES


if __name__ == '__main__':
	print('bot.py found that it was the main module. You should be invoking the bot from entrypoint.py')
	sys.exit(1)
