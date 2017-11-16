import io
import core.blame
import core.handles
import discord


PM_PRIVACY_ERROR = '**Note:** The following message was supposed to be sent to you privately, but your privacy settings didn\'t allow for it.'


class Module:

	''' A module is a blob designed to handle a set of related
		commands, such as setting handling or rendering latex.
	'''

	def __init__(self):
		self.master = None
		self.client = None
		self.shard_id = 0
		self.shard_count = 1

	# Functions used by the system

	def collect_by_type(self, type):
		items = []
		for name, item in self.__class__.__dict__.items():
			if isinstance(item, type):
				items.append(item)
		return items


	def collect_background_tasks(self):
		''' Returns a list of the module's background tasks. '''
		return self.collect_by_type(core.handles.BackgroundTask)

	def collect_startup_tasks(self):
		''' Returns a list of the module's startup tasks. '''
		return self.collect_by_type(core.handles.StartupTask)

	def collect_command_handlers(self):
		''' Returns a list of the module's command handlers. '''
		commands = []
		for name, item in self.__class__.__dict__.items():
			if isinstance(item, core.handles.Command):
				# print('Registered command:', item.name, '(', item.format, ')')
				# if item.perm_setting:
				# 	print(' - Setting:', item.perm_setting)
				# if item.on_edit:
				# 	print(' - Has edit handler')
				commands.append(item)
		return commands

	def collect_message_handlers(self):
		''' Returns a list of the module's message handlers. '''
		return self.collect_by_type(core.handles.OnMessage)

	def collect_edit_handlers(self):
		''' Returns a list of the module's edit handlers. '''
		return self.collect_by_type(core.handles.OnEdit)

	def collect_reaction_handlers(self):
		''' Returns a list of the module's reaction handlers. '''
		return self.collect_by_type(core.handles.ReactionHandler)

	def collect_member_join_handlers(self):
		''' Returns a list of the module's member join handlers. '''
		return self.collect_by_type(core.handles.OnMemberJoined)

	# Functions used by the end user

	async def send_message(self, *args, blame = None, **kwargs):
		''' Send a message and assign blame to it. *args are the
			arguments passed to discord.py's Client.send_message
		'''
		result = await self.client.send_message(*args, **kwargs)
		await core.blame.set_blame(result.id, blame)
		return result

	async def send_private_fallback(self, to, fallback, message, blame = None, supress_warning = False):
		''' Try and send a private message to a user. If it fails,
			post it publicly with a warning.
		'''
		blame = blame or to
		try:
			await self.send_message(to, message, blame = blame)
		except discord.errors.Forbidden:
			if not supress_warning:
				await self.send_message(fallback, PM_PRIVACY_ERROR, blame = blame)
			await self.send_message(fallback, message, blame = blame)

	async def send_file(self, *args, blame = None, **kwargs):
		''' Send a file and assign a blame to the message.
			*args are the arguments passed to discrd.py's
			Client.send_file function.
		'''
		result = await self.client.send_file(*args, **kwargs)
		await core.blame.set_blame(result.id, blame)
		return result

	async def send_image(self, channel, image, fname, content = None, blame = None):
		''' Sends a PIL Image (?) '''
		fobj = io.BytesIO()
		image.save(fobj, format = 'PNG')
		fobj = io.BytesIO(fobj.getvalue())
		if content:
			return await self.send_file(channel, fobj, filename = fname, content = content, blame = blame)
		else:
			return await self.send_file(channel, fobj, filename = fname, blame = blame)
