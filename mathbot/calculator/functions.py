import weakref
import calculator.errors
import functools


class BuiltinFunction:

	def __init__(self, func, name = None):
		self.func = func
		self.name = name or getattr(func, '__name__', '<unnamed>')
		self.macro = False
		
	def __call__(self, *args):
		return self.func(*args)

	def __str__(self):
		return 'Builtin Function {}'.format(self.name)


class Function:

	def __init__(self, address, scope, macro): # , variadic):
		self.address = address
		self.scope = scope
		self.macro = macro
		self.cache = {}
		# self.variadic = variadic
		# assert(not (macro and variadic))

	def __repr__(self):
		return ('m' if self.macro else 'f') + '({})'.format(self.address)


class Array:

	macro = False

	def __init__(self, items):
		self.items = items

	def __call__(self, index):
		return self.items[index]

	def __len__(self):
		return len(self.items)

	def __str__(self):
		if len(self.items) < 5:
			return 'array(' + ', '.join(map(str, self.items)) + ')'
		else:
			return 'array(' + ', '.join(map(str, self.items[:4])) + ', ...)'

	def __repr__(self):
		return str(self)


class Interval:

	macro = False

	def __init__(self, start, gap, length):
		self.start = start
		self.gap = gap
		self.length = length

	def __call__(self, index):
		assert(index < self.length)
		return self.start + self.gap * index

	def __len__(self):
		return self.length

	def __str__(self):
		return 'interval({} : {})'.format(self.start, self.start + self.length * self.gap)

	def __repr__(self):
		return str(self)


class Expanded:

	def __init__(self, arrays):
		# assert(isinstance(array, Array))
		self.arrays = arrays
		self.length = sum(map(len, arrays))

	def __len__(self):
		return self.length

	def __str__(self):
		return 'expanded({})'.format(', '.join(map(str, self.array.items)))