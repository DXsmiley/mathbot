import core.module
import core.handles

GREETING_MESSAGE = '''\
Welcome to the MathBot server!
Type `=help` to get started with the bot.
'''

class GreeterModule(core.module.Module):

    # These are the server IDs of the MathBot server, and my personal development server.
    @core.handles.on_member_joined(servers = ['233826358369845251', '134074627331719168'])
    async def greet(self, member):
        await self.send_message(member, GREETING_MESSAGE, blame = member)
