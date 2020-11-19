# Bytecode that gets included with every program that runs.
# This contains a number of builtin functions and things.

import math
import cmath
import itertools
import os
import sympy
import types
import collections
import functools

from calculator.bytecode import *
from calculator.functions import *
from calculator.errors import EvaluationError
import calculator.parser as parser
import calculator.formatter as formatter
import calculator.crucible as crucible


ALL_SYMPY_CLASSES = tuple(sympy.core.all_classes)


def protect_sympy_function(func):
	def replacement(*args):
		for i in args:
			if not isinstance(i, ALL_SYMPY_CLASSES):
				raise TypeError
		return func(*args)
	replacement.__name__ = func.__name__
	return replacement


def is_function(val):
	return int(isinstance(val, (Function, BuiltinFunction)))


def is_sequence(val):
	return int(isinstance(val, (Array, ListBase)))


def format_normal(val):
	try:
		string = formatter.format(val, limit=5000)
	except calculator.errors.TooMuchOutputError:
		raise calculator.errors.EvaluationError('repr function received object that was too large')
	else:
		glyphs = list(map(Glyph, string))
		return create_list(glyphs)


def is_string(val):
	return is_sequence(val) and all(isinstance(i, Glyph) for i in val)


def format_smart(val):
	if is_string(val):
		if not val:
			return EMPTY_LIST
		try:
			string = formatter.format(val, limit=5000)
		except calculator.errors.TooMuchOutputError:
			raise calculator.errors.EvaluationError('repr function received object that was too large')
		else:
			glyphs = list(map(Glyph, string[1:-1]))
			return create_list(glyphs)
	return format_normal(val)


def array_length(val):
	if not isinstance(val, (Array, Interval, ListBase)):
		raise EvaluationError('Cannot get the length of non-array object')
	return len(val)


def array_expand(*arrays):
	for i in arrays:
		if not isinstance(i, (Array, ListBase)):
			raise EvaluationError('Cannot expand something that\'s not an array or list')
	return Expanded(arrays)


def make_range(start, end):
	start = int(start)
	end = int(end)
	if not isinstance(start, int):
		raise EvaluationError('Cannot create range on non-int')
	if not isinstance(end, int):
		raise EvaluationError('Cannot create range on non-int')
	if end < start:
		raise EvaluationError('Cannot create backwards ranges')
	return Interval(start, 1, end - start)


@protect_sympy_function
def mylog(e, b = 10):
	return sympy.log(e, b)


@protect_sympy_function
def to_degrees(r):
	return r * sympy.Number(180) / sympy.pi


@protect_sympy_function
def to_radians(d):
	return d * sympy.pi / sympy.Number(180)


def glyph_to_int(glyph):
	if not isinstance(glyph, Glyph):
		raise EvaluationError('ord received non-glyph')
	return sympy.Integer(ord(glyph.value))


def int_to_glyph(integer):
	if not isinstance(integer, (int, sympy.Integer)):
		raise EvaluationError('chr received non-integer')
	return Glyph(chr(int(integer)))


@protect_sympy_function
def reduce_to_float(value):
	return sympy.Number(float(value))


BUILTIN_FUNCTIONS = {
	'log': mylog,
	'ln': sympy.log,
	'is_function': is_function,
	'is_sequence': is_sequence,
	'length': array_length,
	'expand': array_expand,
	'int': sympy.Integer,
	'decimal': reduce_to_float,
	'float': reduce_to_float,
	'subs': lambda expr, symbol, value: expr.subs(symbol, value),
	'deg': to_degrees,
	'rad': to_radians,
	'repr': format_normal,
	'str': format_smart,
	'ord': glyph_to_int,
	'chr': int_to_glyph,
}


BUILTIN_COROUTINES = {}


FIXED_VALUES = {
	'π': sympy.pi,
	'τ': sympy.pi * 2,
	'tau': sympy.pi * 2,
	'φ': sympy.S.GoldenRatio,
	'phi': sympy.S.GoldenRatio,
	'ϕ': (1 - math.sqrt(5)) / 2,
	'phiconj': (1 - math.sqrt(5)) / 2,
	'true': True,
	'false': False
}


FIXED_VALUES_EXPORTABLE = {
	'π': math.pi,
	'τ': math.pi * 2,
	'φ': (1 + math.sqrt(5)) / 2,
	'ϕ': (1 - math.sqrt(5)) / 2,
	'pi': math.pi,
	'tau': math.pi * 2,
	'phi': (1 + math.sqrt(5)) / 2,
	'phiconj': (1 - math.sqrt(5)) / 2,
	'true': True,
	'false': False
}


def _extract_from_sympy():
	def _wrap_with_crucible(function, condition=lambda x: True):
		async def _replacement(*args):
			if condition(*args):
				return await crucible.run(function, args, timeout=2)
			return function(*args)
		return protect_sympy_function(_replacement)
	names = '''
		re im sign Abs arg conjugate 
		sin cos tan cot sec csc sinc asin acos atan acot asec acsc atan2 sinh cosh
		tanh coth sech csch asinh acosh atanh acoth asech acsch ceiling floor frac
		exp root sqrt pi E I gcd lcm
		oo:infinity:∞ zoo:complex_infinity nan:not_a_number
	'''
	for i in names.split():
		parts = i.split(':')
		internal_name = parts[0]
		external_names = parts[1:] or [internal_name]
		value = getattr(sympy, internal_name)
		for name in map(str.lower, external_names):
			if isinstance(value, (sympy.FunctionClass, types.FunctionType)):
				BUILTIN_FUNCTIONS[name] = protect_sympy_function(value)
			else:
				FIXED_VALUES[name] = value
	BUILTIN_COROUTINES['factorial'] = _wrap_with_crucible(sympy.factorial, lambda x: x > 100)
	BUILTIN_COROUTINES['gamma'] = _wrap_with_crucible(sympy.gamma, lambda x: x > 100)
_extract_from_sympy()


# Code that is really useful to it's included by default
with open(os.path.join(os.path.dirname(__file__), 'library.c5')) as f:
	LIBRARY_CODE = f.read()


def _assignment_code(name, value, add_terminal_byte=False):
	return {
		'#': 'assignment',
		'variable': {
			'string': name,
		},
		'value': {
			'#': '_exact_item_hack',
			'value': value
		}
	}


def _prepare_runtime(exportable=False):
	if exportable:
		for name, value in FIXED_VALUES_EXPORTABLE.items():
			yield _assignment_code(name, value)
	else:
		for name, value in FIXED_VALUES.items():
			yield _assignment_code(name, value)
		for name, func in BUILTIN_FUNCTIONS.items():
			yield _assignment_code(name, BuiltinFunction(func, name))
		for name, func in BUILTIN_COROUTINES.items():
			yield _assignment_code(name, BuiltinFunction(func, name, is_coroutine=True))
	_, ast = parser.parse(LIBRARY_CODE, source_name='_system_library')
	yield ast


@functools.lru_cache(4)
def prepare_runtime(builder, **kwargs):
	return  builder.build(*list(_prepare_runtime(**kwargs)), unsafe=True)


def wrap_simple(ast):
	builder = CodeBuilder()
	return wrap_with_runtime(builder, ast)
