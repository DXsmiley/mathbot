import abc
import sympy

from .tokenizer import Token as TToken
from .evaluable import Evaluable
from .thunk import Thunk
from .environment import Environment
from .list import *
from .function import *
from .util import foldr
from .errors import EvaluationError, EvaluationEscapeHandler
from .peek import peek


class TreeNode(Evaluable):
	def __getitem__(self, key):
		self._error_token = None
		if key == '#':
			return self.name
		return getattr(self, name)

	# @abc.abstractmethod
	# def eval(self, environment):
	# 	...

	def fulleval(self, environment):
		value = self.eval(environment)
		while isinstance(value, Evaluable):
			value = value.fulleval(environment)
		return value

	# Funky syntax used to ascribe error tokens.
	# TreeNode(thing, thing) | error_token
	def __or__(self, error_token):
		self._error_token = error_token
		return self


def convert_number(x):
	x = x.lower()
	if x.endswith('i'):
		return sympy.I * convert_number(x[:-1])
	if '.' in x and 'e' not in x:
		i, p = x.split('.')
		k = len(p)
		if k < 30: # Maybe increase this limit
			return sympy.Rational(int(i or '0') * 10 ** k + int(p or '0'), 10 ** k)
	return sympy.Number(x.lstrip('0') or '0')


class Number(TreeNode):

	__slots__ = ['token']

	def __init__(self, token):
		self.token = token

	def eval(self, environment):
		return convert_number(str(self.token))

	def __str__(self):
		return self.token.string


class Word(TreeNode):

	simple = True

	def __init__(self, token):
		self.token = token

	def eval(self, environment):
		try:
			r = environment.get(self.token.string)
			if isinstance(r, Thunk):
				r.add_error_context(self.token)
			return r
		except KeyError:
			raise EvaluationError(f'Variable "{self.token.string}" is not defined').at(self.token)

	def __str__(self):
		return self.token.string


class Program(TreeNode):

	def __init__(self, bindings, expressions):
		# self.bindings = bindings
		self.expressions = expressions
		self.bindings = bindings

	def eval(self, environment):
		new_env = Environment(environment, {
			str(i.label): i.value for i in self.bindings
		})
		return [expr.fulleval(new_env) for expr in self.expressions]

	def __str__(self):
		return ',\n'.join(map(str, self.bindings + self.expressions))


class Constant(TreeNode):

	def __init__(self, value):
		self.value = value

	def eval(self, environment):
		return self.value

	def __str__(self):
		return str(self.value)


class BinaryOperator(TreeNode):

	def __init__(self, left, token, right):
		self.left = left
		self.right = right
		self.token = token
		assert isinstance(token, TToken)

	@staticmethod
	@abc.abstractmethod
	def function(a, b):
		pass

	def eval(self, environment):
		with EvaluationEscapeHandler(self.token):
			lt = Thunk(environment, self.left)
			rt = Thunk(environment, self.right)
			return self.function(lt, rt)

	def __str__(self):
		return f'({self.left} {self.token.string} {self.right})'

class AdditionOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() + b.fulleval()

class SubtractionOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() - b.fulleval()

class ProductOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() * b.fulleval()

class DivisionOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() / b.fulleval()

class ModulusOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() % b.fulleval()

class PowerOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() ** b.fulleval()

class LogicalAndOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() and b.fulleval()

class LogicalOrOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return a.fulleval() or b.fulleval()

class PrependOperator(BinaryOperator):
	@staticmethod
	def function(a, b):
		return List(a, b)


class UnaryOperator(TreeNode):
	def __init__(self, op, value):
		assert isinstance(op, TToken)
		self.op = op
		self.value = value

	def eval(self, environment):
		with EvaluationEscapeHandler(self.op):
			return self.function(
				Thunk(environment, self.value)
			)
		# except EvaluationError as e:
		# 	raise e.at(self.op)
		# except Exception:
		# 	raise EvaluationError(f'Cannot perform operation {self.op.string} on {peek(self.value)}').at(self.op)

	@staticmethod
	@abc.abstractmethod
	def function():
		pass

	def __str__(self):
		# This only supports prepend operators
		return f'({self.op}{self.value})'

class UnaryOperatorAfter:
	''' Mixin for unary operators where the operator comes after the.
	'''
	def __str__(self):
		return f'({self.value}{self.op})'

class FactorialOperator(UnaryOperatorAfter, UnaryOperator):
	@staticmethod
	def function(x):
		return sympy.factorial(x.fulleval())

class MinusOperator(UnaryOperator):
	@staticmethod
	def function(x):
		return -x.fulleval()

class LogicalNotOperator(UnaryOperator):
	@staticmethod
	def function(x):
		return sympy.Number(int(not x.fulleval()))

class HeadOperator(UnaryOperator):
	@staticmethod
	def function(x):
		return x.fulleval().head

class TailOperator(UnaryOperator):
	@staticmethod
	def function(x):
		return x.fulleval().tail


class ComparisonChain(TreeNode):

	compaison_ops = {
		'<':  lambda a, b: a < b,
		'>':  lambda a, b: a > b,
		'<=': lambda a, b: a <= b,
		'>=': lambda a, b: a >= b,
		'==': lambda a, b: True if a is b else a == b,
		'!=': lambda a, b: False if a is b else a != b
	}

	def __init__(self, items):
		self.first = items[0]
		self.operators = items[1::2]
		self.values = items[2::2]

	def eval(self, environment):
			prev = self.first.fulleval(environment)
			vs = [i.fulleval(environment) for i in self.values]
			for op, v in zip(self.operators, vs):
				try:
					if not self.compaison_ops[str(op)](prev, v):
						return False
					prev = v
				except EvaluationError as e:
					print(op)
					raise e.at(op)
				except Exception:
					raise EvaluationError(f'Cannot perform operation {op.string} on ' + peek(prev) + ' and ' + peek(v)).at(op)
			return True

	def __str__(self):
		return f'({self.first}' + ''.join(f' {o} {v}' for o, v in zip(self.operators, self.values)) + ')'


class Apply(TreeNode):
	def __init__(self, function, argument):
		self.function = function
		self.argument = argument

	def eval(self, environment):
		f = self.function.eval(environment)
		return f(Thunk(environment, argument))

	def __str__(self):
		return f'({self.function})({self.argument})'


class FunctionDefinition(TreeNode):
	def __init__(self, parameter_list, expression):
		self.parameter_list = parameter_list
		self.expression = expression

	def eval(self, environment):
		return Function(environment, self.parameter_list.names(), self.expression)

	def __str__(self):
		return f'({self.parameter_list} -> {self.expression})'


class Assignment(TreeNode):
	def __init__(self, label, value):
		self.label = label
		self.value = value

	def eval(self, environment):
		return environment.add_recursive_thunk(self.label, self.value)

	def __str__(self):
		if isinstance(self.value, FunctionDefinition):
			return f'{self.label}{self.value.parameter_list} = {self.value.expression}'
		return f'{self.label} = {self.value}'


class FunctionCall(TreeNode):

	def __init__(self, function, arguments, token=None):
		self.function = function
		self.arguments = arguments
		self.token = token

	def eval(self, environment):
		func = self.function.fulleval(environment)
		thunks = [Thunk(environment, i) for i in self.arguments]
		with EvaluationEscapeHandler(self.token):
			return func(thunks)

	def __str__(self):
		return f'{self.function}({", ".join(map(str, self.arguments))})'


class ListLiteral(TreeNode):

	def __init__(self, elements):
		self.elements = elements

	def eval(self, environment):
		if len(self.elements) == 0:
			return Nil()
		thunks = [Thunk(environment, i) for i in self.elements]
		return foldr(List, thunks, Nil())

	def __str__(self):
		return '[' + ', '.join(map(str, self.elements)) + ']'


class ParameterList:

	def __init__(self, parameters):
		self.parameters = parameters

	def eval(self, environment): # This should never be called.
		raise NotImplementedError

	def __str__(self):
		if len(self.parameters) == 1:
			return str(self.parameters[0])
		return '(' + ' '.join(map(str, self.parameters)) + ')'

	def names(self):
		return list(map(str, self.parameters))


class If(TreeNode):

	__slots__ = ['condition', 'then', 'otherwise']

	def __init__(self, condition, then, otherwise):
		self.condition = condition
		self.then = then
		self.otherwise = otherwise

	def eval(self, environment):
		if self.condition.fulleval(environment):
			return self.then.eval(environment)
		else:
			return self.otherwise.eval(environment)


class Percentage(TreeNode):

	def __init__(self, operator, value):
		self.operator = operator
		self.value = value

	def eval(self, environment):
		# Probably broken, will need proper error handling
		return self.value.fulleval(environment) / 100

	def __str__(self):
		return f'%({self.value})'


def _builtin_if(c, a, b):
	if Thunk.resolve_maybe(c):
		return a
	return b

builtin_if = Constant(BuiltinFunction('if', 3, _builtin_if))


class MergeableProgram:

	''' A 'program' that can take additional bindings to it. '''

	def __init__(self):
		self.bind_mapping = {
			'if': builtin_if
		}
		self.protection_levels = {}

	def merge_definitions(self, bindings, protection_level=0):
		for i in bindings:
			label = str(i.label)
			if protection_level < self.protection_levels.get(label, 0):
				raise Exception(f'Cannot override {label}')
			self.bind_mapping[label] = i.value
			self.protection_levels[label] = protection_level

	def eval_expressions(self, expressions):
		binds = [Assignment(k, v) for k, v in self.bind_mapping.items()]
		env = Environment.new_self_refferential_over_thunks(binds)
		return [expr.fulleval(env) for expr in expressions]


class Undefined:

	def eval(self, _):
		raise Exception('Should not have poked this')


if __name__ == '__main__':
	
	def add(a, b):
		return a.eval() + b.eval()

	e1 = BinaryOperator(Constant(1), Constant(2), add)
	print(e1.fulleval(None))

	e2 = Head(ListPrepend(Constant(1), Undefined))
	print(e2.fulleval(None))