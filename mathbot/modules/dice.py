# encoding: utf-8
''' Module to allow the user to roll dice '''

import re
import random

import core.help
import core.settings
import core.util
from discord.ext.commands import Cog, Context
from discord.ext.commands.hybrid import hybrid_command

import math

core.help.load_from_file('./help/roll.md')

FORMAT_REGEX = re.compile(r'^(?:(\d*)[ d]+)?(\d+)$')


class DiceException(Exception): pass


class ValuesTooBigException(DiceException): pass


class DiceModule(Cog):

	''' Module to allow the user to roll dice '''

	@hybrid_command()
	@core.settings.command_allowed('c-roll')
	@core.util.respond
	async def roll(self, ctx: Context, dice: str) -> str:
		''' Roll command. `dice` should be of the format `2d6` or similar. '''
		return await self.handle_roll(ctx, dice, should_sort=True)

	@hybrid_command()
	@core.settings.command_allowed('c-roll')
	@core.util.respond
	async def rollu(self, ctx: Context, dice: str) -> str:
		''' Variant of the roll command that does not sort the output. '''
		return await self.handle_roll(ctx, dice, should_sort=False)

	async def handle_roll(self, ctx: Context, arg: str, should_sort: bool) -> str:
		match = FORMAT_REGEX.match(arg.strip('`'))
		if match is None or match.group(2) is None:
			return '🎲 Format your rolls like `2d6`.'
		dice, faces = match.group(1, 2)
		dice = int(dice or 1)
		if dice <= 0:
			return '🎲 At least one dice must be rolled.'
		faces = int(faces or 6)
		if faces <= 0:
			return '🎲 Dice must have a positive number of faces.'

		limit = await self.get_limit(ctx)

		# this is the minimal length of this query, it is used to determine
		# whether it's possible for the result to be short enough to fit
		# within the limit.
		#
		# I got this by assuming each die rolled 1, plus 1 space per die
		# giving me 2 * dice. Then i add the length of the total, and the
		# length of the extra stuff that's always in the result.
		min_len = 2 * dice + 9 + math.log10(dice)

		# gaussian roll is faster so try that if we can't show all the rolls
		if min_len >= limit:
			total = 0
			try:
				total = self.gaussian_roll(dice, faces)
			except ValuesTooBigException:
				return '🎲 Values are too large.'

			return f'🎲 total: {total}'
		else:
			rolls, total = self.formatted_roll(dice, faces, should_sort=should_sort)
			final_message = f'🎲 {rolls}'
			return final_message if len(final_message) <= limit else f'🎲 total: {total}'

	async def get_limit(self, ctx):
		''' Get the character limit for messages. '''
		unlimited = await ctx.bot.settings.resolve_message('f-roll-unlimited', ctx.message)
		return 2000 if unlimited else 200

	def formatted_roll(self, dice, faces, should_sort=True):
		''' Roll dice and return a string of the results as well as the total. '''
		rolls = [random.randint(1, faces) for _ in range(dice)]
		total = sum(rolls)
		ordered_rolls = sorted(rolls) if should_sort else rolls
		s = f'{" ".join(map(str, ordered_rolls))} (total: {total})'
		return (s if dice > 1 else str(total)), total

	def gaussian_roll(self, dice, faces, limit=100000):
		''' [random.randint(1, faces) for _ in range(dice)]
			Simulate a roll using normal distributions. Do it as
			many times as neccessary to avoid float inaccuracy, unless that means
			rolling more times than limit.
		'''
		# if it passes this first test, then it's safe to do it in one roll
		# 53 is how many bits of precision we have with python's doubles. This
		# means that if we have a number which is greater than 2.0^53 the
		# precision will fall and we can only generate even numbers
		#
		# faces gets squared in the formula, so we need to check against half of 26
		PREC = 53

		if math.log2(faces) < (PREC / 2) and math.log2(dice * faces) < PREC:
			return self.gaussian_roll_single(dice, faces)
		# passing this second test means we can do multiple rolls safely
		elif math.log2(faces) < (PREC / 2):
			dice_per = 2**(PREC - round(math.log2(faces)))
			times = round(dice / dice_per)
			if times > limit:
				raise ValuesTooBigException()
			return sum([self.gaussian_roll_single(dice_per, faces) for _ in range(times)])
		else:
			raise ValuesTooBigException()

	def gaussian_roll_single(self, dice, faces):
		''' Use a normal distribution to roll some dice. Method hits float
			inaccuracies rather easily. In order to avoid float inaccuracy you'll need
			to make sure that:
			1. dice has fewer than 16 digits
			2. faces has fewer than 8 digits
			3. dice and faces have fewer than 16 digits combined
		'''
		mean = (faces + 1) * dice / 2
		std = math.sqrt((dice * (faces * faces - 1)) / 12)
		return int(random.gauss(mean, std))

def setup(bot):
	return bot.add_cog(DiceModule())
