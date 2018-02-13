import re
import random
import asyncio

import core.module
import core.handles
import core.help
import core.settings

core.help.load_from_file('./help/roll.md')

FORMAT_REGEX = re.compile(r'^(?:(\d*)[ d]+)?(\d+)$')

class DiceModule(core.module.Module):

	@core.handles.command('roll', '*')
	@core.handles.reply_with_return
	async def command_roll(self, message, arg):
		match = FORMAT_REGEX.match(arg.strip('`'))
		if match is None or match.group(2) is None:
			return '🎲 Format your rolls like `2d6`.'
		dice, faces = match.group(1, 2)
		dice  = int(dice or 1)
		faces = int(faces or 6)
		if faces > 100000 or dice > 100000:
			return '🎲 Values are too large. Cannot be greater than 100000.'

		rolls, total = self.formatted_roll(dice, faces)
		final_message = f'🎲 {rolls}'
		limit = await self.get_limit(message)
		print(limit)
		return final_message if len(final_message) <= limit else f'🎲 total: {total}'

	async def get_limit(self, message):
		unlimited = await core.settings.resolve_message('f-roll-unlimited', message)
		print(unlimited)
		return 100 if not unlimited else 2000

	def formatted_roll(self, dice, faces):
		rolls = [random.randint(1, faces) for _ in range(dice)]
		s = f'{str.join(" ", (str(i) for i in rolls))} (total: {sum(rolls)})'
		return s, sum(rolls)
