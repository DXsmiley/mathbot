import sympy

from .thunk import Thunk
from .environment import Environment


class BaseFunction:
	pass


class Function(BaseFunction):

	def __init__(self, environment, argument_names, expression):
		self.argument_names = argument_names
		self.environment = environment
		self.expression = expression
		self.memo = {}

	def __call__(self, arguments):
		# Add new variables to environment
		mapping = {name: value for name, value in zip(self.argument_names, arguments)}
		env = Environment(self.environment, mapping)
		if len(arguments) == len(self.argument_names):
			# TODO: Make this memozation thing optional
			_ae = tuple(Thunk.resolve_maybe(i) for i in arguments)
			if all(isinstance(i, sympy.Number) for i in _ae):
				if _ae in self.memo:
					return self.memo[_ae]
				result = self.expression.fulleval(env)
				self.memo[_ae] = result
				return result
			else:
				return self.expression.fulleval(env)
		return Function(env, self.argument_names[len(arguments):], self.expression)	


class BuiltinFunction(BaseFunction):

	def __init__(self, name, num_arguments, function, already_given=[]):
		self.name = name
		self.already_given = already_given
		self.num_arguments = num_arguments
		self.function = function

	def __call__(self, arguments):
		count = len(self.already_given) + len(arguments)
		nargs = self.num_arguments
		if count == nargs:
			return self.function(*(self.already_given + arguments))
		if count > nargs:
			raise Exception(f'Too many arguments for builtin function {self.name}')
		return BuiltinFunction(self.name + '~', nargs - count, self.function, self.already_given + arguments)

	def run_call(self, environment, arguments):
		values = [i.fulleval(environment) for i in arguments]


class NonPartialBuiltinFunction(BaseFunction):

	''' A builtin function that cannot be called partially '''

	def __init__(self, function):
		self.function = function

	def __call__(self, arguments):
		return self.function(*map(Thunk.resolve_maybe, arguments))
