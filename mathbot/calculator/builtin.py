class BuiltinFunction:

	def __init__(self, func, name = None):
		self.func = func
		self.name = name or func.__name__
		
	def call(self, *args):
		return self.func(*args)

	def __str__(self):
		return 'Builtin Function {}'.format(self.name)
