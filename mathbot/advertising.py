import core.parameters
import core.keystore
import patrons
import random

async def should_advertise_to(user, channel):
	result = False
	if core.parameters.get('advertising enable'):
		if patrons.tier(user.id) == patrons.TIER_NONE:
			chan_id = channel.id if channel.is_private else channel.server.id
			ad_count = (await core.keystore.get('advert_counter', chan_id)) \
			        or core.parameters.get('advertising starting-amount')
			if ad_count > core.parameters.get('advertising interval'):
				print('Did advertise!')
				ad_count = 0
				result = True
			else:
				ad_count += random.choice([1, 2])
			await core.keystore.set('advert_counter', chan_id, ad_count)
	return result
