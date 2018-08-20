import patrons
import random

async def should_advertise_to(bot, user, channel):
	result = False
	if bot.parameters.get('advertising enable'):
		if patrons.tier(bot.parameters, user.id) == patrons.TIER_NONE:
			chan_id = channel.id if channel.is_private else channel.server.id
			ad_count = (await bot.keystore.get('advert_counter', chan_id)) \
			        or bot.parameters.get('advertising starting-amount')
			if ad_count > bot.parameters.get('advertising interval'):
				print('Did advertise!')
				ad_count = 0
				result = True
			else:
				ad_count += random.choice([1, 2])
			await bot.keystore.set('advert_counter', chan_id, ad_count)
	return result
