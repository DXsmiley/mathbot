import re
import random
import asyncio

import core.module
import core.handles
import core.help

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
		message = f'🎲 {rolls}'
		return message if len(message) <= 2000 else f'🎲 total: {total}'
	
	def formatted_roll(self, dice, faces):
		rolls = [random.randint(1, faces) for _ in range(dice)]
		s = f'{str.join(" ", (str(i) for i in rolls))} (total: {sum(rolls)})'
		return s, sum(rolls)
