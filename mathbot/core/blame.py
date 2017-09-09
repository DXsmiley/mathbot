import core.keystore

async def set_blame(message_id, blame):
	''' Assigns blame to a particular message.
		i.e. specifies the user that the was responsible for causing the
		bot the send a particular message.
	'''
	if blame is None:
		print('Warning: Sending a message without a blame flag')
	else:
		await core.keystore.set('blame', message_id, blame.mention, expire = 60 * 60 * 80)
