#!/usr/bin/env python3
# encoding: utf-8

import sys
import os
import asyncio

import discord

import logging

import modules.wolfram
import modules.about
import modules.blame
import modules.calcmod
import modules.help
import modules.throws
import modules.settings
import modules.latex
import modules.purge
import modules.echo
import modules.analytics

import core.manager
import core.keystore
import core.parameters

keystore_mode = core.parameters.get('keystore mode')
if keystore_mode == 'redis':
	core.keystore.setup_redis(
		core.parameters.get('keystore redis url'),
		core.parameters.get('keystore redis number')
	)
elif keystore_mode == 'disk':
	core.keystore.setup_disk(core.parameters.get('keystore disk filename'))
else:
	raise Exception('"{}" is not a valid keystore mode'.format(keystore_mode))


RELEASE = core.parameters.get('release').lower()
TOKEN = core.parameters.get('token')

if RELEASE not in ['development', 'beta', 'production']:
	raise Exception('"{}" is not a valid release mode'.format(RELEASE))

if not TOKEN:
	raise Exception('No token specified')

logging.basicConfig(level = logging.INFO)


# Used to ensure the beta bot only replies in the channel that it is supposed to
def event_filter(channel):
	return (RELEASE != 'beta') or ((not channel.is_private) and channel.id == '325908974648164352')


def create_manager(shard_id, shard_count):

	assert(0 <= shard_id < shard_count)

	manager = core.manager.Manager(
		TOKEN,
		shard_id = shard_id,
		shard_count = shard_count,
		master_filter = event_filter
	)

	# New modules go here
	manager.add_modules(
		modules.help.HelpModule(),
		modules.wolfram.WolframModule(),
		modules.settings.SettingsModule(),
		modules.blame.BlameModule(),
		modules.about.AboutModule(),
		modules.latex.LatexModule(),
		modules.calcmod.CalculatorModule(RELEASE in ['development', 'beta']),
		modules.purge.PurgeModule(),
		# Will only trigger stats if supplied with tokens
		modules.analytics.AnalyticsModule()
	)

	if RELEASE == 'development':
		manager.add_modules(
			modules.throws.ThrowsModule(),
			modules.echo.EchoModule()
		)

	return manager


total_shards = core.parameters.get('shards total')
my_shards = core.parameters.get('shards mine')

if total_shards is None:
	print('Total number of shards is unknown. Cannot run.')

print('Total shards:', total_shards)
print('My shards:', ' '.join(map(str, my_shards)))

managers = []
for shard in my_shards:
	managers.append(create_manager(shard, total_shards).run_async())

future = asyncio.gather(*managers)
loop = asyncio.get_event_loop()
loop.run_until_complete(future)
