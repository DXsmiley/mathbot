import abc
from calculator.tokenizer import Token as TToken
from calculator.util import foldr
import sympy


class TreeNode(abc.ABC):
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
		while isinstance(value, (TreeNode, Thunk)):
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

	def __init__(self, token):
		self.token = token

	def eval(self, environment):
		return convert_number(str(self.token))

	def __str__(self):
		return self.token.string


class Word(TreeNode):

	def __init__(self, token):
		self.token = token

	def eval(self, environment):
		return environment.get(self.token.string)

	def __str__(self):
		return self.token.string


class Environment:

	def __init__(self, super, mapping):
		self.super = super
		self.mapping = mapping

	def get(self, name):
		name = name.lower()
		if name in self.mapping:
			return self.mapping[name]
		if self.super is None:
			raise KeyError(name)
		return self.super.get(name)

	def add(self, name, value):
		return Environment(self, {name.lower(): value})

	def __str__(self):
		return f'{self.super}-{self.mapping}'

	@staticmethod
	def new_self_refferential_over_thunks(binds, super=None):
		mapping = {}
		env = Environment(super, mapping)
		for b in binds:
			mapping[str(b.label)] = Thunk(env, b.value)
		return env


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


class MergeableProgram:

	''' A 'program' that can take additional bindings to it. '''

	def __init__(self):
		self.bind_mapping = {}
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
		return self.function(
			Thunk(environment, self.left),
			Thunk(environment, self.right)
		)

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
		return self.function(
			Thunk(environment, self.value)
		)

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
		return not x.fulleval()

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
			if not self.compaison_ops[str(op)](prev, vs):
				return False
			prev = v
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
		raise NotImplementedError

	def __str__(self):
		if isinstance(self.value, FunctionDefinition):
			return f'{self.label}{self.value.parameter_list} = {self.value.expression}'
		return f'{self.label} = {self.value}'


class FunctionCall(TreeNode):
	def __init__(self, function, arguments):
		self.function = function
		self.arguments = arguments

	def eval(self, environment):
		function = self.function.fulleval(environment)
		thunks = [Thunk(environment, i) for i in self.arguments]
		return function(thunks)

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


class Function:
	
	def __init__(self, environment, argument_names, expression):
		self.argument_names = argument_names
		self.environment = environment
		self.expression = expression

	def __call__(self, arguments):
		# Add new variables to environment
		env = self.environment
		for name, value in zip(self.argument_names, arguments):
			env = env.add(name, value)
		if len(arguments) == len(self.argument_names):
			return self.expression.fulleval(env)
		return Function(env, self.argument_names[len(arguments):], self.expression)


class BuiltinFunction:

	def __init__(self, name, num_arguments, function, already_given=[]):
		self.name = name
		self.already_given = already_given
		self.num_arguments = num_arguments
		self.function = function

	def __call__(self, arguments):
		count = len(self.already_given) + len(arguments)
		if count == self.num_arguments:
			return self.function(*(self.already_given + arguments))
		if count > self.num_arguments:
			raise Exception(f'Too many arguments for builtin function {self.name}')
		return PartiallyAppliedFunction(self, self.num_arguments - 1)

	def run_call(self, environment, arguments):
		values = [i.fulleval(environment) for i in arguments]


class NonPartialBuiltinFunction:

	''' A builtin function that cannot be called partially '''

	def __init__(self, function):
		self.function = function

	def __call__(self, arguments):
		return self.function(*map(Thunk.resolve_maybe, arguments))


class PartiallyAppliedFunction:

	@staticmethod
	def create(function, num_arguments, value):
		if num_arguments == 0:
			arguments = [value]
			while isinstance(function, PartiallyAppliedFunction):
				arguments.append(function.value)
				function = function.function
			return function.call_in(arguments[::-1])
		else:
			return PartiallyAppliedFunction(function, num_arguments, value)

	def __init__(self, function, num_arguments, value):
		self.function = function
		self.num_arguments = num_arguments
		self.value = None

	def __call__(self, argument):
		return PartiallyAppliedFunction.create(self, self.num_arguments - 1, value)


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


# class ListPrepend(TreeNode):
	
# 	def __init__(self, head, tail):
# 		self.head = head
# 		self.tail = tail
	
# 	def eval(self, environment):
# 		return List(
# 			Thunk(environment, self.head),
# 			Thunk(environment, self.tail)
# 		)

# 	def __str__(self):
# 		return f'({self.head}):({self.tail})'


class Thunk(TreeNode):
	''' Used in evaluation only, and is not really an AST node. '''

	def __init__(self, environment, expression):
		self.environment = environment
		self.expression = expression
		self.value = None

	def eval(self, _=None):
		return self.fulleval()

	def fulleval(self, _=None):
		# IDEA: Check for recusion here
		if self.value is None:
			self.value = self.expression.eval(self.environment)
		while isinstance(self.value, (Thunk, TreeNode)):
			self.value = self.value.fulleval(self.environment)
			# del self.expression # Can we throw this away??
		return self.value

	@staticmethod
	def resolve_maybe(value):
		if isinstance(value, Thunk):
			return value.fulleval()
		return value


# class Constant(TreeNode):

# 	def __init__(self, value):
# 		self.value = value

# 	def eval(self):
# 		return self.value


class If(TreeNode):

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


class Nil:

	@property
	def length(self):
		return 0

	def fulleval(self):
		return self

	def __str__(self):
		return '[]'


class List:
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
