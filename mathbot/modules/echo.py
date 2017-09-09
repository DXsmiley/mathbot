# Has a command which echoes whatever text was given to it.
# Used only for testing purposes.

import core.module
import core.handles

class EchoModule(core.module.Module):

	@core.handles.command('echo', '*')
	async def echo(self, message, text):
		await self.send_message(message.channel, text)
