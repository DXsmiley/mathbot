import logging
from discord.ext.commands import Context
from discord.abc import Messageable


LOG = logging.getLogger(__name__)


async def set_blame(keystore, sent, blame):
	''' Assigns blame to a particular message.
		i.e. specifies the user that the was responsible for causing the
		bot the send a particular message.
	'''
	string = f'{blame.mention} ({blame.name}#{blame.discriminator})'
	await keystore.set('blame', sent.id, string, expire = 60 * 60 * 80)
