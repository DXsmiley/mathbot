from .thunk import Thunk


class Environment:

	''' Represents a set of bindings from variable names to
		values. Values should be Thunks.
	'''

	def __init__(self, upper, mapping, *, _dont_copy_mapping=False):
		self.upper = upper
		self.mapping = {key.lower(): value for key, value in mapping.items()}
		if _dont_copy_mapping:
			self.mapping = mapping

	def get(self, name):
		name = name.lower()
		if name in self.mapping:
			return self.mapping[name]
		if self.upper is None:
			raise KeyError(name)
		return self.upper.get(name)

	def add(self, name, value):
		return Environment(self, {name.lower(): value})

	def add_recursive_thunk(self, name, value):
		thunk = Thunk(None, value)
		env = Environment(self, {name.lower(): thunk})
		thunk.environment = env
		return env

	def __str__(self):
		return f'{self.upper}-{self.mapping}'

	@staticmethod
	def new_self_refferential_over_thunks(binds, upper=None):
		mapping = {}
		env = Environment(upper, mapping, _dont_copy_mapping=True)
		for b in binds:
			mapping[str(b.label).lower()] = Thunk(env, b.value)
		return env
