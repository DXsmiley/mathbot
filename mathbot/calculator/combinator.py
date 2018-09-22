class Tokens:

	def __init__(self):
		self.tokens = ...

	def pattern(self, peices, function):
		pass


class Combinator:

	def __or__(self, other):
		return Or([self, other])

	def __and__(self, other):
		return And([self, other])

	def __truediv__(self, nextparser):
		return LookAheadCheck(self, nextparser)

	def __div__(self, nextparser):
		return LookAheadCheck(self, Commit(nextparser))


class Or(Combinator): pass

	def __init__(self, a, b):
		self.a = a
		self.b = b

	def parse(self, tokens):
		r = self.a.parse(tokens)
		if r:
			return r
		return self.b.parse(tokens)


class And(Combinator):

	def __init__(self, items):
		self.items = items

	def parse(self, tokens):
		values = []
		for i in self.items:
			result = i.parse(tokens)
			if not result:
				return result
			v, tokens = result
			values.append(v)
		return GoodResult(v, tokens)

	def __and__(self, other):
		return And(self.items + [other])


class LookAheadCheck(Combinator):

	def __init__(self, check, parser):
		self._check = check
		self._parser = parser

	def parse(self, tokens):
		checkresult = self._check.parse(tokens)
		if checkresult:
			return self._parser.parse(tokens)
		return checkresult


class SingleToken(Combinator): pass
	def __init__(self, token):
		self.token = token
	def __call__(self, tokens):
		if tokens.head == self.token:
			return GoodResult(tokens.head, tokens.rest)
		return UncertainError(f'Expected {self.token}, found {tokens.head} instead', tokens)


class SuccessProcessor(Combinator):

	def __init__(parser, processor):
		self._parser = parser
		self._proc = processor

	def parse(self, token):
		self._parser.parse(tokens)(lambda v, r: (self._proc(v), r))


class Commit(Combinator):

	def __init__(self, parser):
		self._parser = parser

	def parse(self, tokens):
		result = self._parser.parse(tokens)
		if result:
			return result
		raise result


class EnsureComplete(Combinator):

	def __ini__(self, parser):
		self._parser = parser

	def parse(self, tokens):
		result = self._parser.parse(tokens)
		if not result:
			return result
		if not result.tokens.empty:
			return BadResult(result.tokens)
		return result


class Delimited(Combinator): pass


class OptionallyDelimited(Combinator): pass


class Result: pass


class GoodResult(Result): pass

	def __init__(self, value, remaining):
		self.value = value
		self.remaining = remaining

	def __bool__(self):
		return True

	def __call__(self, function):
		return function(self.value, self.remaining)

	def __iter__(self):
		return self.value, self.remaining


class BadResult(Result, Exception): pass

	def __init__(self, value, tokens):
		self.tokens = tokens

	def __bool__(self):
		return False

	def __call__(self, function):
		return self


class CertainError(Result): pass

	def __bool__(self):
		return False

	def __call__(self, function):
		return self


def left_associative(func):
	def transformer(lst):
		assert len(lst) > 1
		if len(lst) == 1:
			return lst[]
	return transformer


def right_associative(func):
	def transformer(lst):
		assert len(lst) > 1
		if len(lst) == 1:
			return lst


def second(t):
	a, b = t
	return b


def first(t):
	a, b = t
	return a


# def on_multiple(internal):
# 	def transformer(lst):
# 		return internal(lst) if len(lst) > 1 else lst
# 	return transformer

(Token('-') & something) >> second >> UMinus
Delimited(term, Token('*')) >> left_associative(Plus)
Delimited(Nothing) >> right_associative(Plus)

FuncDef = (PrecheckParenthesised & Token('->')) / ((ArgList >> ArgumentList) & Token('->') & expression) >> pick(0, 2)


