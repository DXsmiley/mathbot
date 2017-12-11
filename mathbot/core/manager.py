import discord
import asyncio
import collections
import core.module
import core.dreport
import traceback
import core.settings
import core.parse_arguments
import core.blame


DISALLOWED_COMMAND_ERROR = """\
That command may not be used in this location.\
"""


class CommandConflictError(Exception):
	def __init__(self, command):
		self.command = command
	def __str__(self):
		return 'Duplicate entries for command: {}'.format(self.command)


class TooManyRedirects(Exception):
	pass


class RedirectionFailed(Exception):
	pass


class Manager:

	def __init__(self, token, shard_id = 0, shard_count = 1, master_filter = lambda c : True):
		self.master_filter = master_filter
		self.commands = {}
		self.reaction_handlers = collections.defaultdict(lambda : [])
		self.modules = []
		self.raw_handlers_message = []
		self.raw_handlers_edit = []
		self.raw_handlers_member_joined = []
		self.shard_id = shard_id
		self.shard_count = shard_count
		self.client = create_client(self, shard_id, shard_count)
		self.token = token
		self.done_setup = False

	# Add modules to the bot
	def add_modules(self, *modules):
		for i in modules:
			assert isinstance(i, core.module.Module)
		self.modules += modules

	# Setup the internals of the bot
	def setup(self):
		assert(self.done_setup == False)
		for module in self.modules:
			# Tell the modules which shard the bot is, give them the client object
			module.shard_id = self.shard_id
			module.shard_count = self.shard_count
			module.client = self.client
			# Assign the background tasks
			for task in module.collect_background_tasks():
				self.client.loop.create_task(task.func(module))
			# Get the command handlers
			for command in module.collect_command_handlers():
				# TODO: Allow commands with the same name that take different arguments
				for name in command.names:
					if name in self.commands:
						raise CommandConflictError(name)
					self.commands[name] = command
				command.module = module
			# Get the message handlers
			for handler in module.collect_message_handlers():
				self.raw_handlers_message.append(handler)
				handler.module = module
			# Get the edit handlers
			for handler in module.collect_edit_handlers():
				self.raw_handlers_edit.append(handler)
				handler.module = module
			# Get the reaction handlers
			for handler in module.collect_reaction_handlers():
				self.reaction_handlers[handler.emoji].append((module, handler))
			# Get the join handlers
			for handler in module.collect_member_join_handlers():
				self.raw_handlers_member_joined.append(handler)
				handler.module = module
		self.done_setup = True

	# Run the bot. Blocking command.
	def run(self):
		if not self.done_setup:
			self.setup()
		self.client.run(self.token)

	# Run the bot asyncronously
	async def run_async(self):
		if not self.done_setup:
			self.setup()
		await self.client.start(self.token)
		print('Shard', self.shard_id, 'has shutdown')

	# Find the proper handler for a given command
	def find_command_handler(self, cmd_string):
		parts = cmd_string.replace('\n', ' ').split(' ')
		for num_parts in range(len(parts), 0, -1):
			joined = ' '.join(parts[:num_parts])
			command = self.commands.get(joined)
			if command is not None:
				arguments = ' '.join(parts[num_parts:])
				return command, arguments
		return None, ''

	async def catch_handler_exception(self, exception, message):
		traceback.print_exc()
		if message.author == self.client.user:
			print('Error while looking at own message.')
			if message.channel.id == core.parameters.get('error-reporting channel'):
				print("IT'S IN THE REPORTING CHANNEL! THIS IS REALLY BAD!")
			else:
				text = 'Error while looking at own message. Not reported to end user.'
				await core.dreport.custom_report(self.client, text)
		else:
			await core.dreport.send(self.client, message.channel, message.content, extra = traceback.format_exc())

	# Handle an incoming message
	async def handle_message(self, message, redirect_count = 0):
		# print(message.author, self.client.user)
		try:
			for handler in self.raw_handlers_message:
				# print('Passing to handler...', handler)
				result = await handler.func(handler.module, message)
				if isinstance(result, core.handles.Redirect):
					message.content = result.destination
					await self.handle_redirect(message, result.destination, 1)
					break
			else:
				cmd_string = await self.check_prefixes(message)
				if cmd_string:
					await self.handle_redirect(message, cmd_string)
		except Exception as e:
			await self.catch_handler_exception(e, message)

	# Handle an incoming meddage edit event
	async def handle_edit(self, before, after):
		try:
			for handler in self.raw_handlers_edit:
				await handler.func(handler.module, before, after)
			cmd_before = await self.check_prefixes(before)
			cmd_after = await self.check_prefixes(after)
			if cmd_after:
				command, arguments = self.find_command_handler(cmd_after)
				if command is not None and command.on_edit is not None:
					await self.exec_edit_command(before, after, command, arguments)
		except Exception as e:
			await self.catch_handler_exception(e, after)

	# Handle redirects. Command handlers are allowed to redirect to other command handlers.
	async def handle_redirect(self, message, cmd_string, redirect_count = 0, is_edit = False):
		if redirect_count > 20:
			raise TooManyRedirects
		command, arguments = self.find_command_handler(cmd_string)
		if command is not None:
			result = await self.exec_command(message, command, arguments)
			if isinstance(result, core.handles.Redirect):
				message.content = result.destination
				await self.handle_redirect(message, result.destination, redirect_count + 1)
		else:
			if redirect_count > 0:
				raise RedirectionFailed

	# Get the reaction handlers for a given emoji
	def get_reaction_handlers(self, emoji):
		yield from self.reaction_handlers[core.handles.ANY_EMOJI]
		if isinstance(emoji, str):
			yield from self.reaction_handlers[emoji]

	# Handle an incoming reaction event
	async def handle_reaction_add(self, reaction, user):
		for module, handler in self.get_reaction_handlers(reaction.emoji):
			# TODO: Filter out reactions that the bot adds.
			if handler.allow_self or user.id != self.client.user.id:
				await handler.func(module, reaction, user)
			# else:
			# 	print('I posted the reaction. Can\'t use it.')

	# Called once the bot connects to Discord
	async def handle_startup(self):
		tasks = []
		for module in self.modules:
			for command in module.collect_startup_tasks():
				tasks.append(command.func(module))
		asyncio.gather(*tasks)

	async def handle_member_joined(self, member):
		for handler in self.raw_handlers_member_joined:
			if handler.servers is None or member.server.id in handler.servers:
				await handler.func(handler.module, member)

	# Actually execute a command! There's so many layers to this stuff...
	async def exec_command(self, message, command, arguments):
		perm = command.perm_setting
		# TODO: Set the default override, check defaults work
		allowed = perm is None or await core.settings.get_setting(message, perm)
		if not allowed:
			# TODO: Fix this up once the blame thing is moved
			result = await self.client.send_message(message.channel, DISALLOWED_COMMAND_ERROR)
			await core.blame.set_blame(result.id, message.author)
		else:
			try:
				arguments = core.parse_arguments.parse(command.format, arguments)
			except core.parse_arguments.InvalidArgumentNumber:
				msg = 'Invalid number of arguments\nSee `=help {}` for help.'.format(command.name)
				result = await self.client.send_message(message.channel, msg)
				await core.blame.set_blame(result.id, message.author)
			except core.parse_arguments.InvalidArgumentType:
				msg = 'One or more arguments were invaluid.\nSee `=help {}` for help.'.format(command.name)
				result = await self.client.send_message(message.channel, msg)
				await core.blame.set_blame(result.id, message.author)
			else:
				return await command.func(command.module, message, *arguments)

	# Execute an edit command.
	async def exec_edit_command(self, before, after, command, arguments):
		perm = command.perm_setting
		# TODO: Set the default override, check defaults work
		allowed = perm is None or await core.settings.get_setting(after, perm)
		if not allowed:
			# TODO: Fix this up once the blame thing is moved
			result = await self.client.send_message(after.channel, DISALLOWED_COMMAND_ERROR)
			await core.blame.set_blame(result.id, after.author)
		else:
			try:
				arguments = core.parse_arguments.parse(command.format, arguments)
			except core.parse_arguments.InvalidArgumentNumber:
				msg = 'Invalid number of arguments\n\nSee `=help {}` for help.'.format(command.name)
				result = await self.client.send_message(after.channel, msg)
				await core.blame.set_blame(result.id, after.author)
			except core.parse_arguments.InvalidArgumentType:
				# This should never happen! Yet...
				assert(False)
			else:
				return await command.on_edit(command.module, before, after, *arguments)

	async def check_prefixes(self, message):
		# Determines whether the command prefix of a message is valid
		# If it is, return the message contents without the prefix
		# Otherwise return none
		content = message.content
		stripped = content.lstrip(' ')
		for prefix in await self.determine_prefixes(message):
			if prefix is not None and content.startswith(prefix):
				return stripped[len(prefix):].strip(' ')
		return None

	# Note that this is being run on *every* message that the bot recieves.
	# That's a lot of redis calls.
	async def determine_prefixes(self, message):
		# Note that both MathBot and DXbot will respond to @mentions
		# of each other. This only impacts the dev environment.
		results = [
			'<@172240092331507712>',
			'<@134073775925886976>',
			'<@325886099937558528>',
			'<@!172240092331507712>',
			'<@!134073775925886976>',
			'<@!325886099937558528>'
		]
		if message.channel.is_private:
			results.append(await core.keystore.get('last-seen-prefix', message.author.id))
			results.append('=')
			results.append('')
		else:
			results.append(await core.settings.get_server_prefix(message.server.id))
		for i, v in enumerate(results):
			if v is not None and not isinstance(v, str):
				print('Non-string prefix detected')
				print(v)
				m = 'Non-string prefix detected: `{}`'.format(str(v))
				await core.dreport.custom_report(self.client, m)
				results[i] = str(v)
		return [i for i in results if i is not None]


def create_client(manager, shard_id, shard_count):

	client = discord.Client(shard_id = shard_id, shard_count = shard_count)
	client._core_ready = False

	@client.event
	async def on_ready():
		print('Shard', manager.shard_id, 'client is ready.')
		await manager.handle_startup()
		client._core_ready = True

	@client.event
	async def on_message(message):
		# print('Received message', message.id)
		# print(message.content)
		if client._core_ready and manager.master_filter(message.channel):
			# print('Handling message')
			await manager.handle_message(message)
		# else:
			# print('Was not ready for the message :(')

	@client.event
	async def on_message_edit(before, after):
		if client._core_ready and manager.master_filter(before.channel):
			await manager.handle_edit(before, after)

	@client.event
	async def on_reaction_add(reaction, user):
		if client._core_ready and manager.master_filter(reaction.message.channel):
			# print(shard_id, 'Reaction add!', reaction.message.id, reaction.emoji)
			await manager.handle_reaction_add(reaction, user)

	@client.event
	async def on_member_join(member):
		if client._core_ready:
			await manager.handle_member_joined(member)

	# @client.event
	# async def on_error(event, *args, **kwargs):
	# 	# If we get here, a RuntimeError has been raised and we need to restart.
	# 	print('RuntimeError noticed. Will shut down in a moment...')
	# 	await client.close()

	return client
