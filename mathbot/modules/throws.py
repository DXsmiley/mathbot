import core.module
import core.handles

class ThrowsModule(core.module.Module):

	@core.handles.command('throw', '')
	async def throw(self, message):
		raise Exception('I wonder what went wrong?')

	@core.handles.command('throw_runtime', '')
	async def throw_runtime(self, message):
		raise RuntimeError('I wonder what went wrong?')
