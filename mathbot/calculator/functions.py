import asyncio

import calculator.errors
import calculator.operators


class Glyph:

	''' Calculator object that represents a single character. '''

	__slots__ = ['value']

	def __init__(self, value):
		if isinstance(value, str) and len(value) == 1:
			self.value = value
		else:
			raise TypeError(f'Cannot create a glyph from a {value.__class__}')

	def __eq__(self, other):
		if not isinstance(other, Glyph):
			raise calculator.errors.EvaluationError('Cannot compare Glyph to non-glyph')
		return self.value == other.value

	def __lt__(self, other):
		if not isinstance(other, Glyph):
			raise calculator.errors.EvaluationError('Cannot compare Glyph to non-glyph')
		return self.value < other.value

	def __str__(self):
		return self.value

	def __hash__(self):
		return ord(self.value)


class BuiltinFunction:

	''' Calculator object that represents a "builtin" function.
		That is, a function
	'''

	def __init__(self, func, name=None):
		self.func = func
		self.name = name or getattr(func, '__name__', '<unnamed>')

	def __call__(self, *args):
		return self.func(*args)

	def __str__(self):
		return 'Builtin Function {}'.format(self.name)


class Function:

	''' Calculator object the represents a function defined by some bytecode. '''

	def __init__(self, address, scope, name):
		# I'm not entirely happy about keeping the name in this thing.
		self.address = address
		self.scope = scope
		self.name = name

	def __repr__(self):
		if self.name == '?':
			return 'Anonymous function @{}'.format(self.address)
		return 'Function {} @{}'.format(self.name, self.address)


class SequenceBase:

	async def __aeq__(a, b):
		if a is b:
			return True
		if not isinstance(b, SequenceBase):
			raise calculator.errors.EvaluationError('Attempted to compare sequence to non-sequence')
		if len(a) != len(b):
			return False
		while a:
			# Let the event loop do work in case this takes a while
			await asyncio.sleep(0)
			if not await calculator.operators.super_equals(a.head, b.head):
				return False
			a = a.rest
			b = b.rest
		return True

	async def __alt__(a, b):
		if a is b:
			return False
		if not isinstance(b, SequenceBase):
			raise calculator.errors.EvaluationError('Attempted to compare sequence to non-sequence')
		while a and b:
			# Let the event loop do work in case this takes a while
			await asyncio.sleep(0)
			if not await calculator.operators.super_equals(a.head, b.head):
				return await calculator.operators.super_less_than(a.head, b.head)
			a = a.rest
			b = b.rest
		# If a still has things, it's greater, False (because longer)
		# If b still has things, it's greater, True
		# If both empty, they're equal, False
		# Result: a < b if b still has stuff
		return bool(b)


class Array(SequenceBase):

	def __init__(self, items, start=None, end=None):
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

	def __iter__(self):
		for i in range(self.start, self.end):
			yield self.items[i]


class ListBase(SequenceBase):

	__slots__ = ['head', 'rest', 'size']

	def __iter__(self):
		current = self
		while current:
			yield current.head
			current = current.rest

	def __repr__(self):
		return 'List-{}'.format(len(self))

	def __bool__(self):
		return True


class List(ListBase):

	__slots__ = ['head', 'rest', 'size']

	def __init__(self, head, rest):
		self.head = head
		self.rest = rest
		self.size = len(rest) + 1

	def __len__(self):
		return self.size

	def __str__(self):
		parts = []
		cur = self
		while not isinstance(cur, EmptyList):
			parts.append(str(cur.head))
			cur = cur.rest
		return 'list(' + ', '.join(parts) + ')'


class FlatList(ListBase):

	class Viewer(ListBase):

		__slots__ = ['fl', 'place']

		def __init__(self, fl, place):
			self.fl = fl
			self.place = place

		@property
		def head(self):
			return self.fl.values[self.place]

		@property
		def rest(self):
			if self.place + 1 == len(self.fl.values):
				return self.fl.tail
			return FlatList.Viewer(self.fl, self.place + 1)

		def __len__(self):
			return self.fl.size - self.place


	__slots__ = ['values', 'tail', 'place', 'size']

	def __init__(self, values, tail):
		if len(values) == 0:
			raise ValueError('Cannot create a FlatList with an empty array of values')
		if tail is None:
			raise ValueError('Tail of FlatList cannot be None')
		self.values = values
		self.tail = tail
		self.size = len(tail) + len(values)

	@property
	def head(self):
		return self.values[0]

	@property
	def rest(self):
		if len(self.values) == 1:
			return self.tail
		return FlatList.Viewer(self, 1)

	def __len__(self):
		return self.size

	def __str__(self):
		parts = []
		cur = self
		while not isinstance(cur, EmptyList):
			parts.append(str(cur.head))
			cur = cur.rest
		return 'list(' + ', '.join(parts) + ')'


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


class SingularValue:

	def __init__(self, item):
		self.item = item

	def __call__(self):
		return self.item

	def __str__(self):
		return 'constant({})'.format(self.item)

	def __repr__(self):
		return repr(self)


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


def create_list(sequence):
	sequence = list(sequence)
	return FlatList(sequence, EMPTY_LIST) if sequence else EMPTY_LIST


EMPTY_LIST = EmptyList()
