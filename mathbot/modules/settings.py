import aioredis
import os
import re
import core.keystore
import core.help
import core.settings

from discord.ext.commands import command, guild_only, has_permissions, Cog


core.help.load_from_file('./help/settings.md')
core.help.load_from_file('./help/theme.md')
core.help.load_from_file('./help/units.md')
core.help.load_from_file('./help/prefix.md')


CHECKSETTING_TEMPLATE = '''\
Setting "{}" has the following values:
```
TextChannel: {}
Server:  {}
Default: {}
```
'''


class ProblemReporter:

	def __init__(self, ctx):
		self.problems = []
		self.ctx = ctx

	async def __aenter__(self):
		return self._report

	async def __aexit__(self, type, value, traceback):
		if self.problems:
			msg = '\n'.join(self.problems)
			await self.ctx.send(msg)
			raise WasProblems

	def _report(self, text):
		self.problems.append(text)


class WasProblems(Exception):
	pass


class SettingsModule(Cog):

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
		True: 'enabled',
		False: 'disabled'
	}.get

	@command(name='set')
	@guild_only()
	@has_permissions(administrator=True)
	async def _set(self, ctx, context: str, setting: str, value: str):
		try:
			async with ProblemReporter(ctx) as problem:
				setting_details = core.settings.details(setting)
				if setting_details is None:
					problem(f'`{setting}` is not a valid setting. See `=help settings` for a list of valid settings.')
				if context not in ['server', 'guild', 'channel', 's', 'c', 'g']:
					problem(f'`{context}` is not a valid context. Options are: `server` or `channel`')
				if value not in ['enable', 'disable', 'original', 'e', 'd', 'o', 'reset', 'r']:
					problem(f'`{value}` is not a valid value. Options are `enable`, `disable`, `reset`.')
		except WasProblems:
			pass
		else:
			context = ctx.message.channel if context[0] == 'c' else ctx.message.guild
			val = SettingsModule.reduce_value(value)
			await ctx.bot.settings.set(setting, context, val)
			await ctx.send('Setting applied.')

	@command()
	async def theme(self, ctx, theme):
		theme = theme.lower()
		if theme not in ['light', 'dark']:
			return f'`{theme}` is not a valid theme. Valid options are `light` and `dark`.'
		await ctx.bot.keystore.set(f'p-tex-colour:{ctx.message.author.id}', theme)
		await ctx.send(f'Your theme has been set to `{theme}`.')

	@command()
	async def units(self, ctx, units: str):
		units = units.lower()
		if units not in ['metric', 'imperial']:
			await ctx.send(f'`{units}` is not a unit system. Valid units are `metric` and `imperial`.')
		else:
			await ctx.bot.keystore.set(f'p-wolf-units:{ctx.author.id}', units)
			await ctx.send(f'Your units have been set to `{units}`.')

	@command()
	@guild_only()
	async def checksetting(self, ctx, setting):
		if core.settings.details(setting) is None:
			return '`{}` is not a valid setting. See `=help settings` for a list of valid settings.'
		value_server = await ctx.bot.settings.get_single(setting, ctx.message.guild)
		value_channel = await ctx.bot.settings.get_single(setting, ctx.message.channel)
		print('Details for', setting)
		print('Server: ', value_server)
		print('Channel:', value_channel)
		default = core.settings.details(setting).get('default')
		await ctx.send(CHECKSETTING_TEMPLATE.format(
			setting,
			SettingsModule.expand_value(value_channel),
			SettingsModule.expand_value(value_server),
			SettingsModule.expand_value(default)
		))

	@command()
	@guild_only()
	async def checkallsettings(self, ctx):
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
			value_channel = await ctx.bot.settings.get_single(setting, ctx.message.channel)
			value_server = await ctx.bot.settings.get_single(setting, ctx.message.guild)
			lines.append(' {: <16} | {: <8} | {: <8} | {: <8}'.format(
				setting,
				SettingsModule.expand_value(value_channel),
				SettingsModule.expand_value(value_server),
				SettingsModule.expand_value(s_details['default'])
			))
		await ctx.send('```\n{}\n```'.format('\n'.join(lines)))

	@command()
	async def checkdmsettings(self, ctx):
		lines = [
			' Setting          | Default  | Resolved ',
			'------------------+----------+----------'
		]
		items = [
			(core.settings.get_cannon_name(name), details)
			for name, details in core.settings.SETTINGS.items()
			if 'redirect' not in details
		]
		for setting, s_details in sorted(items, key=lambda x: x[0]):
			resolved = await ctx.bot.settings.resolve_message(setting, ctx.message)
			lines.append(' {: <16} | {: <8} | {: <8}'.format(
				setting,
				SettingsModule.expand_value(s_details['default']),
				resolved
			))
		await ctx.send('```\n{}\n```'.format('\n'.join(lines)))

	@command()
	@guild_only()
	async def prefix(self, ctx, *, arg=''):
		prefix = await ctx.bot.settings.get_server_prefix(ctx.message.guild)
		p_text = prefix or '='
		if p_text in [None, '=']:
			m = 'The prefix for this server is `=`, which is the default.'
		else:
			m = f'The prefix for this server is `{p_text}`, which has been customised.'
		if arg:
			m += '\nServer admins can use the `setprefix` command to change the prefix.'
		await ctx.send(m)

	@command()
	@guild_only()
	@has_permissions(administrator=True)
	async def setprefix(self, ctx, *, new_prefix):
		prefix = new_prefix.strip().replace('`', '')
		await ctx.bot.settings.set_server_prefix(ctx.guild, prefix)
		await ctx.send(f'Bot prefix for this server has been changed to `{prefix}`.')

def setup(bot):
	return bot.add_cog(SettingsModule())
