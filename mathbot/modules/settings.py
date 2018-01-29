import aioredis
import os
import re
import core.keystore
import core.help
import core.settings
import core.module


SETTING_COMMAND_ARG_ERROR = """
Invalid number of arguments.
Usage:
	`=set context setting value`
Type `=help settings` for more information.\
"""


SETTING_COMMAND_PRIVATE_ERROR = """
The `settings` command cannot be used in a private channel.
Type `=help settings` for more information.\
"""


SETTING_COMMAND_PERMS_ERROR = """
You need to be an admin on this server to use this command here.
"""


SETTING_COMMAND_RESPONSE = """\
The following setting has been applied:
```
Setting: {setting}
Value: {value}
Context: {context}
```
"""


core.help.load_from_file('./help/settings.md')
core.help.load_from_file('./help/theme.md')
core.help.load_from_file('./help/prefix.md')


INVALID_SETTING_MESSAGE = '''\
Invalid setting "{setting}".

The following settings exist:
{valid_settings}

See `=help settings` for more details.
'''


INVALID_CONTEXT_MESSAGE = '''\
Invalid context parameter "{context}".

Setting "{setting}" supports the following contexts:
{valid_contexts}

See `=help settings` for more details.
'''


INVALID_VALUE_MESSAGE = '''\
Invalid value parameter "{value}".

Setting "{setting}" supports the following values:
{valid_values}

See `=help settings` for more details.
'''


CHECKSETTING_TEMPLATE = '''\
Setting "{}" has the following values:
```
Server:  {}
Channel: {}
You:     {}
```
'''


def format_bullet_points(l):
	return '\n'.join(map(lambda c: ' - ' + c, l))


GLOBAL_ELEVATION = {
	'133804143721578505' # DXsmiley
}


def is_admin_message(m, prevent_global_elevation = False):
	if m.channel.is_private:
		return True
	if m.author.id in GLOBAL_ELEVATION and not prevent_global_elevation:
		return True
	perms = m.channel.permissions_for(m.author)
	return perms.administrator or perms.manage_server


class SettingsModule(core.module.Module):

	@core.handles.command('settings setting set', 'string string string')
	async def command_set(self, message, context, setting, value):
		setting, setting_details = core.settings.redirect(setting)
		# Throw an error for an unknown setting.
		if setting_details is None:
			valid_settings = format_bullet_points(sorted(core.settings.SETTINGS))
			msg = INVALID_SETTING_MESSAGE.format(setting = setting, valid_settings = valid_settings)
			return await self.send_message(message.channel, msg, blame = message.author)
		# Ensure that the context is valid
		if context not in setting_details['contexts']:
			valid_contexts = format_bullet_points(setting_details['contexts'])
			msg = INVALID_CONTEXT_MESSAGE.format(context = context, setting = setting, valid_contexts = valid_contexts)
			return await self.send_message(message.channel, msg, blame = message.author)
		# If the context is the channel or the server, check that the user has the correct permissions to apply it.
		# Also give an error if this is done from a private message.
		if context in ['channel', 'server']:
			if message.channel.is_private:
				return await self.send_message(message.channel,
					'Cannot apply setting to context "{}" from private message.'.format(context),
					blame = message.author
				)
			if not is_admin_message(message):
				return await self.send_message(message.channel, SETTING_COMMAND_PERMS_ERROR, blame = message.author)
		# Check that the value supplied is valid
		if value not in setting_details['values']:
			valid_values = format_bullet_points(setting_details['values'])
			msg = INVALID_VALUE_MESSAGE.format(value = value, setting = setting, valid_values = valid_values)
			return await self.send_message(message.channel, msg, blame = message.author)
		# NOTE: Be careful with this if you go to change it at any point
		mapped_value = setting_details['values'][value]
		value_reduction = {
			True: 1,
			False: 0,
			None: 0
		}
		key = core.settings.get_key(message, setting, context)
		await core.keystore.set(key, value_reduction.get(mapped_value, mapped_value))
		if mapped_value is None:
			await core.keystore.delete(key)
		response = SETTING_COMMAND_RESPONSE.format(
			context = context,
			setting = setting,
			value = value
		)
		await self.send_message(message.channel, response, blame = message.author)

	@core.handles.command('theme', 'string')
	async def command_theme(self, message, theme):
		theme = theme.lower()
		if theme not in ['light', 'dark']:
			m = '`{theme}` is not a valid theme. Valid options are `light` and `dark`.'
		else:
			key = core.settings.get_key(message, 'p-tex-colour', 'self')
			await core.keystore.set(key, theme)
			m = 'Your theme has been set to `{theme}`.'
		await self.send_message(message.channel, m.format(theme = theme), blame = message.author)

	@core.handles.command('checksetting', 'string')
	async def command_checksetting(self, message, arg):
		arg, details = core.settings.redirect(arg)
		if details is None:
			m = 'Setting "{}" does not exist.'.format(arg)
			await self.send_message(message.channel, m, blame = message.author)
		else:
			s = c = 'private channel'
			if not message.channel.is_private:
				s = await core.settings.get_setting_context(message, arg, 'server')
				c = await core.settings.get_setting_context(message, arg, 'channel')
			u = await core.settings.get_setting_context(message, arg, 'self')
			r = CHECKSETTING_TEMPLATE.format(arg, s, c, u)
			await self.send_message(message.channel, r, blame = message.author)

	@core.handles.command('prefix', '*')
	async def command_prefix(self, message, arg):
		print('=prefix command')
		if message.channel.is_private:
			await self.send_message(message.channel, 'This command does not apply to private channels', blame = message.author)
		else:
			if arg == '':
				prefix = await core.settings.get_server_prefix(message.server.id)
				if prefix is None or prefix == '=':
					m = 'The prefix for this server is `=`, which is the default.'
				else:
					m = 'The prefix for this server is `{}`, which has been customised.'.format(prefix)
				await self.send_message(message.channel, m, blame = message.author)
			elif not is_admin_message(message):
				await self.send_message(message.channel, 'You must be an admin on this server to change the prefix', blame = message.author)
			else:
				prefix = arg.strip().replace('`', '')
				await core.settings.set_server_prefix(message.server.id, prefix)
				await self.send_message(message.channel, 'Bot prefix for this server has been changed to `{}`.'.format(prefix), blame = message.author)
