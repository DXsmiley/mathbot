import re
import calculator.formatter


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


class EvaluationEscapeHandler:

	__slots__ = ['token']

	def __init__(self, token):
		self.token = token

	def __enter__(self):
		pass

	def __exit__(self, typ, value, traceback):
		if typ is not None:
			if isinstance(value, EvaluationError):
				raise value.at(self.token)
			elif isinstance(value, RecursionError):
				raise EvaluationError('Python stack overflow').at(self.token)
			else:
				raise EvaluationError('Could not perform operation').at(self.token)


class TooMuchOutputError(Exception):
    pass


class FormattedError(Exception):

	def __init__(self, description, *values):
		if len(values) == 0:
			self.description = description
		else:
			formatted = list(map(lambda x: calculator.formatter.format(x, limit = 2000), values))
			self.description = description.format(*formatted)

	def __str__(self):
		return self.description


class CompilationError(Exception):
	''' Problem in the code found during compilation '''

	def __init__(self, description, source = None):
		self.description = description
		if source is None:
			self.position = None
		else:
			self.position = source['source']['position']

	def __str__(self):
		return self.description


class EvaluationError(Exception):

	def __init__(self, description):
		self.description = description

	def __str__(self):
		return f'Error: {self.description}\n'

	def at(self, token):
		return EvaluationErrorLocationContext(token, self)


class EvaluationErrorLocationContext(EvaluationError):
	def __init__(self, token, child):
		self.token = token
		self.child = child

	# This looks O(N^2)
	def __str__(self):
		return f'Error at [location here]\n{make_source_marker_at_token(self.token, 1)}\n{self.child}'



class SystemError(FormattedError):
	''' Problem due to a bug in the system, not the user's code '''


class AccessFailedError(EvaluationError):
	''' Failed to access a variable '''
	def __init__(self, name):
		super().__init__('Failed to access variable {}', name)
		self.name = name


class SelfDependentThunkError(EvaluationError):
	''' A thunk attempted to evaluate itself while it was already evaluating,
		this is a symptom of an infinite loop.
	'''


class TokenizationFailed(Exception):

	def __init__(self, source, location, reason):
		self.source = source
		self.location = location
		self.reason = reason

	def __str__(self):
		return f'Problem during tokenization: {self.reason}\n\n' + make_source_marker_at_location(self.source, self.location)


class ParserFailed(Exception):

	def __int__(self, source, location, reason):
		self.source = source
		self.location = location
		self.reason = reason

	def __str__(self):
		return f'Problem during parsing: {self.reason}\n\n' + make_source_marker_at_location(self.source, self.location)


def make_source_marker_at_location(source, location, lines_around=3):
	lines = source.split('\n')
	cur = source.count('\n', 0, location)
	lines = [
		*lines[cur - lines_around : cur + 1],
		' ' * (location - cur - sum(map(len, lines[:cur]))) + '^',
		*lines[cur + 1 : cur + lines_around]
	]
	return '\n'.join(lines)


def make_source_marker_at_token(token, lines_around=3):
	return make_source_marker_at_location(token.source, token.location, lines_around)
