import abc


class TreeNode(abc.ABC):
	def __getitem__(self, key):
		self._error_token = None
		if key == '#':
			return self.name
		return getattr(self, name)

	@abc.abstractmethod
	def eval(self, environment):
		...

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
		self.bind_mapping = {
			i.name: i.expression
			for i in bindings
		}

	def eval(self, environment):
		new_env = Environment(environment, self.bind_mapping)
		return [
			self.eval(new_env, expr)
			for expr in self.expressions
		]


class Constant(TreeNode):

	def __init__(self, value):
		self.value = value

	def eval(self, environment):
		return self.value

	def __str__(self):
		return str(self.value)


class Word(TreeNode):

	def __init__(self, word):
		self.word = word
	
	def eval(self, environment):
		return environment.get_variable(self.word)

	def __str__(self):
		return self.word


class BinaryOperator(TreeNode):
	def __init__(self, left, right, op):
		self.left = left
		self.right = right
		self.op = op

	def eval(self, environment):
		return self.op(
			Thunk(environment, self.left),
			Thunk(environment, self.right)
		)

	def __str__(self):
		return f'({self.left}) {self.op} ({self.right})'


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
	def __init__(self, argument_names, expression):
		self.argument_names = argument_names
		self.expression = expression

	def eval(self, environment):
		return Function(environment, self.argument_names, self.expression)

	def __str__(self):
		return f'({",".join(self.argument_names)}) -> ({self.expression})'


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


class ListPrepend(TreeNode):
	
	def __init__(self, head, tail):
		self.head = head
		self.tail = tail
	
	def eval(self, environment):
		return List(
			Thunk(environment, self.head),
			Thunk(environment, self.tail)
		)

	def __str__(self):
		return f'({self.head}):({self.tail})'


class Head(TreeNode):

	def __init__(self, value):
		self.value = value

	def eval(self, environment):
		return self.value.eval(environment).head


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
			# del self.expression # Can we throw this away??
		return self.value


class If(TreeNode):

	def __init__(self, environment, condition, then, otherwise):
		self.environment = environment
		self.condition = condition
		self.then = then
		self.otherwise = otherwise

	def eval(self, environment):
		if self.condition.fulleval(environment):
			return self.then.eval(environment)
		else:
			return self.otherwise.eval(environment)


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
