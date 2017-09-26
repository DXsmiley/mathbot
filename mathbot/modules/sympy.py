# Can be used by navigating into the mathbot folder
# (outside the modules directory) and running
# python -m modules.sympy

import core.module
import core.handles
import calculator.attempt6
import sympy
import math


class SymPyModule(core.module.Module):

	@core.handles.command('sym', '*')
	async def sym(self, message, text):
		pass


CONSTANTS = {
	# 'e': sympy.exp(1)
}


EXTRACT_FROM_SYMPY = 're im sign Abs arg conjugate polar_lift periodic_argument principal_branch sin cos tan cot sec csc sinc asin acos atan acot asec acsc atan2 sinh cosh tanh coth sech csch asinh acosh atanh acoth asech acsch ceiling floor frac exp log root sqrt diff integrate pi E'


for i in EXTRACT_FROM_SYMPY.split():
	CONSTANTS[i.lower()] = getattr(sympy, i)


class VariableStore:

	def __init__(self):
		self.values = {}

	def get(self, name):
		name = name.lower()
		if name in CONSTANTS:
			return CONSTANTS[name]
		if name not in self.values:
			self.values[name] = sympy.symbols(name)
		return self.values[name]

	def set(self, name, value):
		name = name.lower()
		assert(name not in CONSTANTS)
		self.values[name] = value


class Context:

	def __init__(self):
		self.variables = VariableStore()

	def execute(self, p):
		t = p['#']
		if t == 'number':
			return int(p['string'])
		elif t == 'word':
			return self.variables.get(p['string'])
		elif t == 'bin_op':
			o = p['operator']
			l = self.execute(p['left'])
			r = self.execute(p['right'])
			if o == '+': return l + r
			if o == '-': return l - r
			if o == '*': return l * r
			if o == '/': return l / r
			if o == '^': return l ** r
			raise Exception('Unknown operator {}'.format(o))
		elif t == 'assignment':
			name = p['variable']['string']
			value = self.execute(p['value'])
			self.variables.set(name, value)
		elif t == 'function_call':
			func = self.execute(p['function'])
			arguments = list(map(self.execute, p['arguments']['items']))
			# print(func, arguments)
			return func(*arguments)
		elif t == 'program':
			for i in p['items']:
				result = self.execute(i)
				if result is not None:
					print(result)
		else:
			raise Exception('Unknown node {}'.format(t))


if __name__ ==  '__main__':

	c = Context()

	line = input('> ')
	while line != '':
		_, ast = calculator.attempt6.parse(line)
		# print(ast)
		result = c.execute(ast)
		if result is not None:
			print(result)
		line = input('> ')
