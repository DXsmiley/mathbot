import abc
import tokenizer
from util import foldr

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
		while isinstance(value, TreeNode):
			value = value.eval(environment)
		return value

	# Funky syntax used to ascribe error tokens.
	# TreeNode(thing, thing) | error_token
	def __or__(self, error_token):
		self._error_token = error_token
		return self


class Number(TreeNode):

	def __init__(self, token):
		self.token = token

	def eval(self, environment):
		try:
			return int(self.token.string)
		except:
			return float(self.token.string)

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
		if name in self.mapping:
			return self.mapping[name]
		return self.super.get(name)

	def add(self, name, value):
		return Environment(this, {name: value})


class Program(TreeNode):

	def __init__(self, bindings, expressions):
		# self.bindings = bindings
		self.expressions = expressions
		self.bindings = bindings
		self.bind_mapping = {
			i.label: i.value
			for i in bindings
		}

	def eval(self, environment):
		new_env = Environment(environment, self.bind_mapping)
		return [
			self.eval(new_env, expr)
			for expr in self.expressions
		]

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
		assert isinstance(token, tokenizer.Token)

	def eval(self, environment):
		return self.function(
			Thunk(environment, self.left),
			Thunk(environment, self.right)
		)

	def __str__(self):
		return f'({self.left} {self.token.string} {self.right})'

class AdditionOperator(BinaryOperator):
	function = lambda a, b: a.fulleval() + b.fulleval()

class SubtractionOperator(BinaryOperator):
	function = lambda a, b: a.fulleval() - b.fulleval()

class ProductOperator(BinaryOperator):
	function = lambda a, b: a.fulleval() * b.fulleval()

class DivisionOperator(BinaryOperator):
	function = lambda a, b: a.fulleval() / b.fulleval()

class ModulusOperator(BinaryOperator):
	function = lambda a, b: a.fulleval() % b.fulleval()

class LogicalAndOperator(BinaryOperator):
	function = lambda a, b: a.fulleval() and b.fulleval()

class LogicalOrOperator(BinaryOperator):
	function = lambda a, b: a.fulleval() or b.fulleval()

class PrependOperator(BinaryOperator):
	function = lambda a, b: List(a, b)


class UnaryOperator(TreeNode):
	def __init__(self, op, value):
		assert isinstance(op, tokenizer.Token)
		self.op = op
		self.value = value

	def eval(selv, environment):
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
	function = lambda x: math.factorial(x.fulleval())

class MinusOperator(UnaryOperator):
	function = lambda x: -x.fulleval()

class LogicalNotOperator(UnaryOperator):
	function = lambda x: not x.fulleval()

class HeadOperator(UnaryOperator):
	function = lambda x: x.fulleval().head

class TailOperator(UnaryOperator):
	function = lambda x: x.fulleval().tail


class ComparisonChain(TreeNode):
	def __init__(self, items):
		self.first = items[0]
		self.operators = items[1::2]
		self.values = items[2::2]

	def eval(self, environment):
		thunks = [Thunk(environment, i) for i in [self.first] + self.values]

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
		return Function(environment, self.parameter_list, self.expression)

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

	def __str__(self):
		return f'{self.function}({", ".join(map(str, self.arguments))})'


class ListLiteral(TreeNode):
	def __init__(self, elements):
		self.elements = elements

	def eval(environment):
		if len(self.elements) == 0:
			return Nil
		thunks = [Thunk(environment, i) for i in self.elements]
		return foldr(List, thunks, Constant(Nil))

	def __str__(self):
		return '[' + ', '.join(map(str, self.elements)) + ']'


class Function:
	
	def __init__(self, argument_names, environment, expression):
		self.argument_names = argument_names
		self.environment = environment
		self.expression = expression

	def __call__(self, argument):
		return PartiallyAppliedFunction.create(self, len(self.argument_names) - 1, arugment)

	def run_call(self, environment, arguments):
		mapping = {
			self.argument_names[i]: arguments[i]
			for i in range(len(arguments))
		}
		environment = Environment(self.environment, mapping)
		return self.expression.eval(environment)


class BuiltinFunction:

	def __init__(self, num_arguments, function):
		self.num_arguments = num_arguments
		self.function = function

	def __call__(self, argument):
		return PartiallyAppliedFunction(self, self.num_arguments - 1)

	def run_call(self, environment, arguments):
		values = [i.fulleval(environment) for i in arguments]


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
		return '(' + ', '.join(map(str, self.parameters)) + ')'


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
		while isinstance(self.value, Thunk):
			self.value = self.value.fulleval()
			# del self.expression # Can we throw this away??
		return self.value


class Constant(TreeNode):

	def __init__(self, value):
		self.value = value

	def eval(self):
		return self.value


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

	def __init__(self, environment, operator, value):
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
