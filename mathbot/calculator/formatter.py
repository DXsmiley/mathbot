''' Calculator formatter.

	Used to take complicated data structures, including
	lists, arrays, and sympy objects and convert them
	into a flat, human-readable string.
'''

import sympy
from . import functions
from . import errors
import re


ALL_SYMPY_CLASSES = tuple(sympy.core.all_classes) # pylint: disable=no-member
ELEMENT_SEPARATOR = '  '


class Collector:

	''' Buffers print-like commands in order to make things
		fast and also limit the total size of the output.
	'''

	def __init__(self, limit=None):
		self.parts = []
		self.length = 0
		self.limit = limit

	def print(self, *args):
		''' Add some stuff to the buffer.
			Raises an exception if it overlfows.
		'''
		self.parts += args
		self.length += sum(map(len, args))
		if self.limit and self.length > self.limit:
			raise errors.TooMuchOutputError

	def drop(self):
		''' Remove the last item from the buffer. '''
		self.parts.pop()

	def __str__(self):
		''' Reduce to a string. '''
		output = ''.join(self.parts)
		if self.limit and len(output) > self.limit:
			output = output[:self.limit - 3] + '...'
		return output


class CustomSympyPrinter(sympy.printing.str.StrPrinter):

	def _print_Mul(self, expr):
		string = sympy.printing.str.StrPrinter._print_Mul(self, expr)
		return re.sub(r'^1\.0\*', '', string)

	def _print_ImaginaryUnit(self, expr):
		return 'i'

	def _print_Infinity(self, expr):
		return '∞' if self._settings.get('unicode', True) else 'infinity'

	def _print_NegativeInfinity(self, expr):
		return '-∞' if self._settings.get('unicode', True) else 'negitive_infinity'

	def _print_ComplexInfinity(self, expr):
		return 'complex_infinity'

	def _print_NaN(self, expr):
		return 'not_a_number'

	def _print_Pi(self, expre):
		return 'π' if self._settings.get('unicode', True) else 'pi'

	def _print_Integer(self, expr):
		SEP = '\N{SINGLE LOW-9 QUOTATION MARK}'
		normal = super()._print_Integer(expr)[::-1]
		out = []
		for i, c in enumerate(normal):
			if i % 3 == 0 and i != 0:
				out.append(SEP)
			out.append(c)
		return ''.join(out[::-1]).replace('-' + SEP, '-')


class SimpleFormatter:

	''' Simplest implementation of the formatter.
		Currently used to format things in all cases,
		but in theory could be subclassed to produce
		different behaviour for specific cases.
	'''

	def __init__(self, limit=None):
		self._collector = Collector(limit=limit)

	def drop(self):
		''' Remove the most recently added item '''
		self._collector.drop()

	def fmt(self, *args):
		''' Format a number of objects '''
		for i in args:
			# print(i.__class__, i.__class__.__mro__)
			if i is None:
				self._collector.print('null')
			elif isinstance(i, bool):
				self.fmt_py_bool(i)
			elif isinstance(i, str):
				self.fmt_py_string(i)
			elif isinstance(i, list):
				self.fmt_py_list(i)
			elif isinstance(i, functions.Array):
				self.fmt_array(i)
			elif isinstance(i, functions.ListBase):
				self.fmt_list(i)
			elif isinstance(i, functions.Glyph):
				self.fmt_glyph(i)
			elif isinstance(i, ALL_SYMPY_CLASSES):
				self.fmt_sympy_object(i)
			else:
				self.fmt_py_string(str(i))

	def fmt_py_bool(self, b):
		''' Format a boolean value '''
		self._collector.print('true' if b else 'false')

	def fmt_py_string(self, i):
		''' Format a string, which means just add it to the output '''
		self._collector.print(i)

	def fmt_glyph(self, glyph):
		''' Format a single glyph '''
		o = '\\t' if glyph.value == '\t' else glyph.value
		o = '\\n' if glyph.value == '\n' else o
		self.fmt(o)
		# self.fmt('`', glyph.value, '`')

	def fmt_array(self, array):
		''' Format an array '''
		self.fmt('array(')
		for i in array:
			self.fmt(i, ELEMENT_SEPARATOR)
		self.drop()
		self.fmt(')')

	def fmt_list(self, lst):
		''' Format a list '''
		is_string = True
		for i in lst:
			if not isinstance(i, functions.Glyph):
				is_string = False
		if len(lst) == 0:
			self.fmt('[]')
		elif is_string:
			self.fmt('"')
			for i in lst:
				if i.value == '"':
					self._collector.print('\\"')
				else:
					self._collector.print(i.value)
			self.fmt('"')
		else:
			self.fmt('[')
			for i in lst:
				self.fmt(i, ELEMENT_SEPARATOR)
			self.drop()
			self.fmt(']')

	def fmt_py_list(self, lst):
		''' Format a python list '''
		self.fmt('(')
		for i in lst:
			self.fmt(i, ', ') # leave alone as it needs to remain Python syntax
		if lst:
			self.drop()
		self.fmt(')')

	def fmt_sympy_object(self, obj):
		''' Format a sympy object '''
		self._collector.print(sympy_cleanup(CustomSympyPrinter().doprint(obj)))

	def __str__(self):
		return str(self._collector)


def format(*values, limit=None): # pylint: disable=redefined-builtin
	''' Format some values, producing a human-readable string. '''
	fmtr = SimpleFormatter(limit=limit)
	fmtr.fmt(*values)
	return str(fmtr)


def sympy_cleanup(string):
	return string.replace('**', '^').replace('*', '×')


ESCAPE_REGEX = re.compile(r'\\(.)')
ESCAPE_DICT = {'n': '\n', 't': '\t'}

def string_backslash_escaping(string):
	return ESCAPE_REGEX.sub(lambda x: ESCAPE_DICT.get(x.group(1), x.group(1)), string)
