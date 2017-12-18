import weakref
import calculator.errors
import functools


class BuiltinFunction:

	def __init__(self, func, name = None):
		self.func = func
		self.name = name or getattr(func, '__name__', '<unnamed>')
		
	def __call__(self, *args):
		return self.func(*args)

	def __str__(self):
		return 'Builtin Function {}'.format(self.name)


class Function:

	def __init__(self, address, scope, name):
		# I'm not entirely happy about keeping the name in this thing.
		self.address = address
		self.scope = scope
		self.name = name

	def __repr__(self):
		if self.name == '?':
			return 'Anonymous function @{}'.format(self.address)
		return 'Function {} @{}'.format(self.name, self.address)


class Array:

	def __init__(self, items, start = None, end = None):
		self.items = items
		self.start = start or 0
		self.end = end or len(items)

	@property
	def head(self):
		if self.start >= self.end:
			raise calculator.errors.EvaluationError('Attempted to get head of an empty Array')
		return self.items[self.start]

	@property
	def rest(self):
		if self.start >= self.end:
			raise calculator.errors.EvaluationError('Attempted to get tail of an empty Array')
		return Array(self.items, self.start + 1, self.end)

	def __call__(self, index):
		try:
			if self.start + index >= self.end:
				raise IndexError
			return self.items[self.start + index]
		except Exception:
			raise calculator.errors.EvaluationError('Invalid array index')

	def __len__(self):
		return self.end - self.start

	def __bool__(self):
		return self.start < self.end

	def __str__(self):
		if len(self) < 5:
			return 'array(' + ', '.join(map(str, self.items[self.start:self.end])) + ')'
		else:
			return 'array(' + ', '.join(map(str, self.items[self.start:self.start + 4])) + ', ...)'

	def __repr__(self):
		return str(self)


class ListBase:
	pass


class List(ListBase):

	def __init__(self, head, rest):
		self.head = head
		self.rest = rest
		self.size = len(rest) + 1

	def __len__(self):
		return self.size

	def __bool__(self):
		return True

	def __str__(self):
		parts = []
		cur = self
		while not isinstance(cur, EmptyList):
			parts.append(str(cur.head))
			cur = cur.rest
		return 'list(' + ', '.join(parts) + ')'

	def __repr__(self):
		return 'List-{}'.format(self.size)


class EmptyList(ListBase):

	def __len__(self):
		return 0

	def __bool__(self):
		return False

	@property
	def head(self):
		raise calculator.errors.EvaluationError('Attempt to get head of empty list')

	@property
	def rest(self):
		raise calculator.errors.EvaluationError('Attempted to get the tail of an empty list')

	def __str__(self):
		return '.'

	def __repr__(self):
		return 'List-0'


class SingularValue:

	def __init__(self, item):
		self.item = item

	def __call__(self):
		return self.item

	def __str__(self):
		return 'constant({})'.format(self.item)

	def __repr__(self):
		return str(self)


class Interval:

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
		return 'expanded_sequences'
		# return 'expanded({})'.format(', '.join(map(str, self.array.items)))

	def __iter__(self):
		for i in self.arrays:
			if not isinstance(i, (Array, ListBase)):
				raise calculator.errors.EvaluationError('Cannot expand something that\'s not a list or an array')
			cur = i
			while cur:
				yield cur.head
				cur = cur.rest