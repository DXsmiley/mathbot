import re
import random
import asyncio

import core.module
import core.handles
import core.help

core.help.load_from_file('./help/roll.md')

FORMAT_REGEX = re.compile(r'^(?:(\d*)[ d]+)?(\d+)$')

class DiceModule(core.module.Module):

	@core.handles.command('roll', '*', perm_setting='c-roll')
	@core.handles.reply_with_return
	async def command_roll(self, message, arg):
		match = FORMAT_REGEX.match(arg.strip('`'))
		if match is None or match.group(2) is None:
			return '🎲 Format your rolls like `2d6`.'
		dice, faces = match.group(1, 2)
		dice  = int(dice or 1)
		faces = int(faces or 6)
		if faces <= 0:
			return '🎲 Dice must have a positive number of faces.'
		if faces > 100000 or dice > 100000:
			return '🎲 Values are too large. Cannot be greater than 100000.'
		total = sum(random.randint(1, faces) for i in range(dice))
		return f'🎲 {total}'
