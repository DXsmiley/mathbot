from functools import reduce
from .evaluable import Evaluable
from .errors import SelfDependentThunkError, EvaluationError

class Thunk(Evaluable):
	''' Used in evaluation only, and is not really an AST node. '''

	__slots__ = ['environment', 'expression', 'value', 'running', 'error_contexts']

	def __init__(self, environment, expression):
		self.environment = environment
		self.expression = expression
		self.value = None
		self.running = False
		self.error_contexts = []

	def eval(self, _=None):
		return self.fulleval()

	def add_error_context(self, token):
		self.error_contexts.append(token)

	def fulleval(self, _=None):
		# IDEA: Check for recusion here
		if self.running:
			raise SelfDependentThunkError('Infinite recursion detected')
		try:
			self.running = True
			if self.value is None:
				self.value = self.expression.eval(self.environment)
			while isinstance(self.value, Evaluable):
				self.value = self.value.fulleval(self.environment)
				# del self.expression # Can we throw this away??
			return self.value
		except EvaluationError as e:
			raise reduce(lambda x, c: x.at(c), self.error_contexts, e)
		finally:
			self.running = False

	def peek(self):
		if self.value is None:
			yield '?'

	@staticmethod
	def resolve_maybe(value):
		if isinstance(value, Thunk):
			return value.fulleval()
		return value
