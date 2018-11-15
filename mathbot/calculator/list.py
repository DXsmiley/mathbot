from .thunk import Thunk


class ListBase:
	pass


class List(ListBase):
	def __init__(self, head, tail):
		self._head = head
		self._tail = tail

	@property
	def head(self):
		return self._head

	@property
	def tail(self):
		return self._tail

	@property
	def length(self):
		return self._tail.fulleval().length + 1

	def fulleval(self):
		return self

	def __str__(self):
		r = ['[']
		c = self
		while not isinstance(c, Nil):
			r.append(str(Thunk.resolve_maybe(c.head)))
			r.append(', ')
			c = Thunk.resolve_maybe(c.tail)
		r[-1] = ']'
		return ''.join(r)


class Nil(ListBase):

	@property
	def length(self):
		return 0

	def fulleval(self):
		return self

	def __str__(self):
		return '[]'
