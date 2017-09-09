import core.manager
import core.mock.client

def MockManager(core.manager.Manager):

	def __init__(self, legacy_adaptor = None):
		self.commands = {}
		self.modules = []
		self.client = core.mock.client.Client()
		self.token = token
		self.done_setup = False
		self.legacy_adaptor = legacy_adaptor

	async def send_message(self, )
