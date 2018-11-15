from .thunk import Thunk
from .list import List, Nil
from .function import Function, BuiltinFunction, NonPartialBuiltinFunction


class Backspace: pass


def _peek(x):
	if isinstance(x, Thunk):
		if x.value is None:
			yield '?'
		else:
			yield from _peek(x.value)
	elif isinstance(x, List):
		yield '['
		while not isinstance(x, (Nil, Thunk)):
			yield from _peek(x.head)
			yield ', '
			x = x.tail
		yield Backspace
		if isinstance(x, Thunk):
			yield ' ...?]'
		else:
			yield ']'
	elif isinstance(x, Nil):
		yield '[]'
	elif isinstance(x, BuiltinFunction):
		yield f'(Builtin function {x.name})'
	else:
		yield str(x)


def buildstring(generator):
	stack = []
	for i in generator:
		if i is Backspace:
			stack.pop()
		else:
			stack.append(i)
	return ''.join(stack)


def peek(thing):
	return buildstring(_peek(thing))
