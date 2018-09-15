import logging
from discord.ext.commands import Context
from discord.abc import Messageable


LOG = logging.getLogger(__name__)


def monkey_patch():
	Context.send = _context_send


async def set_blame(keystore, sent, blame):
	''' Assigns blame to a particular message.
		i.e. specifies the user that the was responsible for causing the
		bot the send a particular message.
	'''
	string = f'{blame.mention} ({blame.name}#{blame.discriminator}, {blame.nick or "*no nickname*"})'
	await keystore.set('blame', sent.id, string, expire = 60 * 60 * 80)


async def _context_send(context, *args, **kwargs):
	sent = await Messageable.send(context, *args, **kwargs)
	# LOG.info(f'Setting blame for {sent.id}: {context.message.author}')
	await set_blame(context.bot.keystore, sent, context.message.author)
	return sent
