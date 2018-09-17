import patrons
import random
import discord
from utils import is_private

MESSAGES = [
    'Every little bit helps',
    'Keep it running',
]

class AdvertisingMixin:

    async def advertise_to(self, user, channel, destination):
        if self.parameters.get('advertising enable') and (await self.patron_tier(user.id)) == patrons.TIER_NONE:
            chan_id = str(channel.id if is_private(channel) else channel.guild.id)
            counter = (await self.keystore.get('advert_counter', chan_id)) or 0
            interval = self.parameters.get('advertising interval')
            await self.keystore.set('advert_counter', chan_id, counter + 1)
            if counter % interval == 0:
                await destination.send(embed=discord.Embed(
                    title='Support the bot on Patreon!',
                    description=random.choice(MESSAGES),
                    colour=discord.Colour.blue(),
                    url='https://www.patreon.com/dxsmiley'
                ))
