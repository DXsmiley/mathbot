import re


def wrap_if_plus(s):
	if '+' in s or '-' in s:
		return '(' + s + ')'
	return s


def format_value(x):
	if x is None:
		return 'null'
	if isinstance(x, complex):
		real = wrap_if_plus(format_value(x.real))
		imag = wrap_if_plus(format_value(x.imag))
		if real != '0' and imag != '0':
			return '{}+{}**i**'.format(real, imag)
		elif imag != '0':
			return imag + '**i**'
		else:
			return real
	if isinstance(x, int):
		return str(x)
	if isinstance(x, float):
		if abs(x) < 1e-22:
			return '0'
		if abs(x) > 1e10 or abs(x) < 1e-6:
			s = '{:.8e}'.format(x)
			return re.sub(r'\.?0*e', 'e', s)
		return '{:.8f}'.format(x).rstrip('0').rstrip('.')
	return '"{}"'.format(str(x))


class EvaluationError(Exception):
	''' Things that go wrong at runtime '''

	def __init__(self, description):
		self.description = description

	def __str__(self):
		return self.description


class CompilationError(Exception):
	''' Problem in the code found during compilation '''

	def __init__(self, description):
		self.description = description

	def __str__(self):
		return self.description


class SystemError(Exception):
	''' Problem due to a bug in the system, not the user's code '''

	def __init__(self, description, *values):
		if len(values) == 0:
			self.description = description
		else:
			formatted = list(map(format_value, values))
			self.description = description.format(*formatted)

	def __str__(self):
		return self.description


class DomainError(EvaluationError):

	def __init__(self, function_name, value):
		self.function_name = function_name
		self.value = value

	def __str__(self):
		return '{} cannot be applied to {}'.format(
			self.function_name,
			format_value(self.value)
		)
