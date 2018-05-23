#!/usr/bin/env python3
# encoding: utf-8

import warnings
warnings.simplefilter('default')

import sys
import os
import asyncio
import re
import signal

import discord
import logging
import core.parameters
import json

import typing


logging.basicConfig(level = logging.INFO)

print(f'Default recursion limit is {sys.getrecursionlimit()}')
print(f'Upgrading to 2500')
sys.setrecursionlimit(2500)


DONE_SETUP = False
RELEASE = None
TOKEN = None
SHARDS_TOTAL = 0
SHARDS_MINE = typing.List[int]
BOT_RUNNING = True


# class SecondSignal(Exception):
# 	def __str__(self):
# 		return 'A second signal was received.'


# def handle_sigterm(signum, frame):
# 	global BOT_RUNNING
# 	if not BOT_RUNNING:
# 		raise SecondSignal
# 	BOT_RUNNING = False
# 	print('\nCaught SIGTERM\n')


# def handle_sigint(signum, frame):
# 	global BOT_RUNNING
# 	if not BOT_RUNNING:
# 		raise SecondSignal
# 	BOT_RUNNING = False
# 	print('\nCaught SIGINT\n')


# signal.signal(signal.SIGTERM, handle_sigterm)
# signal.signal(signal.SIGINT, handle_sigint)



def do_setup():
	global DONE_SETUP
	global RELEASE
	global TOKEN
	global SHARDS_TOTAL
	global SHARDS_MINE

	import core.manager
	import core.keystore

	if DONE_SETUP:
		raise Exception('Cannot run setup twice')

	DONE_SETUP = True

	# Setup the keystore

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

	# Determine the release mode and token

	RELEASE = core.parameters.get('release').lower()
	TOKEN = core.parameters.get('token')

	if RELEASE not in ['development', 'beta', 'production']:
		raise Exception('"{}" is not a valid release mode'.format(RELEASE))

	if not TOKEN:
		raise Exception('No token specified')

	SHARDS_TOTAL = core.parameters.get('shards total')
	SHARDS_MINE = core.parameters.get('shards mine')

	if SHARDS_TOTAL is None:
		print('Total number of shards is unknown. Cannot run.')

	print('Total shards:', SHARDS_TOTAL)
	print('My shards:', ' '.join(map(str, SHARDS_MINE)))


# Filters out messages from other bots.
def event_filter(message):
	if RELEASE != 'development' and message.author.bot:
		return False
	return True


def create_shard_manager(shard_id, shard_count):

	# Imports happen in here because importing some of these modules
	# causes state changes that could interfere with tests if they're
	# executed too early.

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
	import modules.reporter
	import modules.greeter
	import modules.dice
	import modules.heartbeat

	assert(0 <= shard_id < shard_count)

	manager = core.manager.Manager(
		TOKEN,
		shard_id = shard_id,
		shard_count = shard_count,
		master_filter = event_filter
	)

	manager.add_modules(
		modules.help.HelpModule(),
		modules.wolfram.WolframModule(),
		modules.settings.SettingsModule(),
		modules.blame.BlameModule(),
		modules.about.AboutModule(),
		modules.latex.LatexModule(),
		modules.calcmod.CalculatorModule(),
		modules.dice.DiceModule(),
		modules.purge.PurgeModule(),
		# Will only trigger stats if supplied with tokens
		modules.analytics.AnalyticsModule(),
		modules.reporter.ReporterModule(),
		modules.heartbeat.Heartbeat()
	)

	if RELEASE == 'production':
		manager.add_modules(
			modules.greeter.GreeterModule()
		)

	if RELEASE == 'development':
		manager.add_modules(
			modules.throws.ThrowsModule(),
			modules.echo.EchoModule()
		)

	return manager


async def run_shard(shard_id, shard_count):
	while BOT_RUNNING:
		manager = create_shard_manager(shard_id, shard_count)
		async def handle_shutdown():
			while BOT_RUNNING:
				await asyncio.sleep(2)
			await manager.shutdown()
		await asyncio.gather(
			manager.run_async(),
			handle_shutdown()
		)


async def finish_or_cancel(task):
	try:
		asyncio.wait_for(task, timeout=10)
	except asyncio.TimeoutError:
		task.cancel()


def run_blocking():
	''' Run the bot '''
	future = run_async()
	loop = asyncio.get_event_loop()
	loop.run_until_complete(future)
	pending = asyncio.Task.all_tasks()
	loop.run_until_complete(asyncio.gather(*pending))
	# for task in asyncio.Task.all_tasks():
	# 	print('Completing task', task)
	# 	loop.run_until_complete(finish_or_cancel(task))
	loop.close()


async def run_async():
	''' Returns a future which will run the bot when awaited '''
	if not DONE_SETUP:
		do_setup()
	coroutines = [run_shard(i, SHARDS_TOTAL) for i in SHARDS_MINE]
	return await asyncio.gather(*coroutines)


if __name__ == '__main__':

	# Load parameters from command line arguments

	for i in sys.argv[1:]:
		if re.fullmatch(r'\w+\.env', i):
			value = os.environ.get(i[:-4])
			jdata = json.loads(value)
			core.parameters.add_source(jdata)
		elif i.startswith('{') and i.endswith('}'):
			jdata = json.loads(i)
			core.parameters.add_source(jdata)
		else:
			core.parameters.add_source_filename(i)

	# Run the bot

	run_blocking()
