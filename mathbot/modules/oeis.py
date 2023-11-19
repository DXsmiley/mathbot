import aiohttp
import json

from urllib.parse import urlencode
from discord.ext.commands import Cog, Context
from mathbot.core.settings import command_allowed
from discord.ext.commands.hybrid import hybrid_command
from mathbot import core

core.help.load_from_file('./mathbot/help/oeis.md')

class OEIS(Cog):

	@hybrid_command()
	@command_allowed('c-oeis')
	async def oeis(self, ctx: Context, *, query=''):
		if query == '':
			await ctx.send(f'The `{ctx.prefix}oeis` command is used to query the Online Encyclopedia of Integer Sequences. See `{ctx.prefix}help oeis` for details.')
			return
		async with ctx.typing():
			async with aiohttp.ClientSession() as session:
				params = {
					'q': query,
					'start': 0,
					'fmt': 'json'
				}
				async with session.get('https://oeis.org/search', params=params, timeout=10) as req:
					j = await req.json()
					# print(json.dumps(j, indent=4))
					count = j.get('count', 0)
					res = j.get('results', None)
					if count == 0:
						await ctx.send('No sequences were found.')
					elif res is None:
						await ctx.send(f'There are {count} relevant sequences. Please be more specific.')
					else:
						name = res[0]['name']
						number = res[0]['number']
						digits = res[0]['data'].replace(',', ', ').strip()
						match_text = (
							f"There were {count} relevant sequences. Here is one:"
							if count > 1
							else "There was 1 relevant sequence:"
						)
						m = f"{match_text}\n\n**{name}**\nhttps://oeis.org/A{number}\n\n{digits}\n"
						# for c in res[0]['comment']:
						# 	if len(m) + len(c) + 10 < 2000:
						# 		m += f'\n> {c}'
						await ctx.send(m)


def setup(bot):
	return bot.add_cog(OEIS())
