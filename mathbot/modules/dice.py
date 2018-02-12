import re
import random
import asyncio

import core.module
import core.handles

FORMAT_REGEX = re.compile(r'^(\d*)[ d]*(\d+)$')

class DiceModule(core.module.Module):

	@core.handles.command('roll', '*')
	@core.handles.reply_with_return
	async def command_roll(self, message, arg):
		match = FORMAT_REGEX.match(arg.strip('`'))
		if match is None or match.group(2) is None:
			return '🎲 Format your rolls like `2d6`.'
		faces, dice = match.group(1, 2)
		faces = int(faces or 1)
		dice  = int(dice or 6)
		if faces > 100000 or dice > 100000:
			return f'🎲 Values are too lage. Cannot be greater than 100000.'
		total = sum(random.randint(1, faces) for i in range(dice))
		return f'🎲 {total}'
