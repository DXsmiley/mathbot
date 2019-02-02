import logging
from discord.ext.commands import Context
from discord.abc import Messageable


LOG = logging.getLogger(__name__)


async def set_blame(keystore, sent, blame):
	''' Assigns blame to a particular message.
		i.e. specifies the user that the was responsible for causing the
		bot the send a particular message.
	'''
	blob = {
		'mention': blame.mention,
		'name': blame.name,
		'discriminator': blame.discriminator,
		'id': blame.id
	}
	await keystore.set_json('blame', sent.id, blob, expire = 60 * 60 * 80)
