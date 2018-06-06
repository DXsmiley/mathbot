import aioredis
import os
import re
import core.keystore
import core.help
import core.settings
import core.module


core.help.load_from_file('./help/settings.md')
core.help.load_from_file('./help/theme.md')
core.help.load_from_file('./help/location.md')
core.help.load_from_file('./help/prefix.md')


CHECKSETTING_TEMPLATE = '''\
Setting "{}" has the following values:
```
Channel: {}
Server:  {}
Default: {}
```
'''


class ProblemReporter:

	def __init__(self, module, channel):
		self.problems = []
		self.module = module
		self.channel = channel

	async def __aenter__(self):
		return self._report

	async def __aexit__(self, type, value, traceback):
		if self.problems:
			msg = '\n'.join(self.problems)
			await self.module.send_message(self.channel, msg)
			raise WasProblems

	def _report(self, text):
		self.problems.append(text)


class WasProblems(Exception):
	pass


class SettingsModule(core.module.Module):

	reduce_value = {
		'enable': 1,
		'disable': 0,
		'reset': None,
		'original': None,
		'e': 1,
		'd': 0,
		'r': None,
		'o': None
	}.get

	expand_value = {
		None: '--------',
		1: 'enabled',
		0: 'disabled',
		True: 'enabled',
		False: 'disabled'
	}.get

	@core.handles.command('settings setting set', 'string string string', no_dm=True, discord_perms='manage_server')
	async def command_set(self, message, context, setting, value):
		try:
			async with ProblemReporter(self, message.channel) as problem:
				setting_details = core.settings.details(setting)
				if setting_details is None:
					problem('`{}` is not a valid setting. See `=help settings` for a list of valid settings.'.format(setting))
				if context not in ['server', 'channel', 's', 'c']:
					problem('`{}` is not a valid context. Options are: `server` or `channel`'.format(context))
				if value not in ['enable', 'disable', 'original', 'e', 'd', 'o', 'reset', 'r']:
					problem('`{}` is not a valid value. Options are `enable`, `disable`, `reset`.'.format(value))
		except WasProblems:
			pass
		else:
			ctx = {'s': message.server, 'c': message.channel}[context[0]]
			val = SettingsModule.reduce_value(value)
			await core.settings.set(setting, ctx, val)
			await self.send_message(message.channel, 'Setting applied.', blame = message.author)

	@core.handles.command('theme', 'string|lower')
	async def command_theme(self, message, theme):
		if theme not in ['light', 'dark']:
			return f'`{theme}` is not a valid theme. Valid options are `light` and `dark`.'
		else:

			key = 'p-tex-colour:' + message.author.id
			await core.keystore.set(key, theme)
			m = 'Your theme has been set to `{theme}`.'
		await self.send_message(message.channel, m.format(theme = theme), blame = message.author)

	@core.handles.command('location', '*')
	async def command_location(self, message, new):
		new = new.strip().replace('\n', ' ')[:300]
		if not new:
			existing = await core.keystore.get('p-wolf-location', message.author.id)
			return f'Your location is `{existing}`.' if existing else 'You have not set a location.'
		await core.keystore.set('p-wolf-location', message.author.id, new)
		return f'Your location has been set to `{new}`.'

	@core.handles.command('checksetting', 'string', no_dm=True)
	async def command_checksetting(self, message, setting):
		if core.settings.details(setting) is None:
			return '`{}` is not a valid setting. See `=help settings` for a list of valid settings.'
		value_server = await core.settings.get_single(setting, message.server)
		value_channel = await core.settings.get_single(setting, message.channel)
		print('Details for', setting)
		print('Server: ', value_server)
		print('Channel:', value_channel)
		default = core.settings.details(setting).get('default')
		return CHECKSETTING_TEMPLATE.format(
			setting,
			SettingsModule.expand_value(value_channel),
			SettingsModule.expand_value(value_server),
			SettingsModule.expand_value(default)
		)

	@core.handles.command('checkallsettings', '', no_dm=True)
	async def command_check_all_settings(self, message):
		lines = [
			' Setting          | Channel  | Server   | Default',
			'------------------+----------+----------+----------'
		]
		items = [
			(core.settings.get_cannon_name(name), details)
			for name, details in core.settings.SETTINGS.items()
			if 'redirect' not in details
		]
		for setting, s_details in sorted(items, key=lambda x: x[0]):
			value_channel = await core.settings.get_single(setting, message.channel)
			value_server = await core.settings.get_single(setting, message.server)
			lines.append(' {: <16} | {: <8} | {: <8} | {: <8}'.format(
				setting,
				SettingsModule.expand_value(value_channel),
				SettingsModule.expand_value(value_server),
				SettingsModule.expand_value(s_details['default'])
			))
		reply = '```\n{}\n```'.format('\n'.join(lines))
		await self.send_message(message, reply)

	@core.handles.command('prefix', '*', no_dm=True)
	async def command_prefix(self, message, arg):
		if arg:
			return core.handles.Redirect('setprefix', arg)
		prefix = await core.settings.get_server_prefix(message.server)
		if prefix is None or prefix == '=':
			return 'The prefix for this server is `=`, which is the default.'
		return 'The prefix for this server is `{}`, which has been customised.'.format(prefix)


	@core.handles.command('setprefix', '*', no_dm=True, discord_perms='manage_server')
	async def command_set_prefix(self, message, arg):
		prefix = arg.strip().replace('`', '')
		await core.settings.set_server_prefix(message.server, prefix)
		await self.send_message(message, 'Bot prefix for this server has been changed to `{}`.'.format(prefix))
