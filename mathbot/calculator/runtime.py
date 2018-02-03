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
import calculator.operators as operators
import calculator.parser as parser


def except_math_error(f, name = None):
	name = name or f.__name__
	def internal(*x):
		try:
			return f(*x)
		except EvaluationError as e:
			raise e
		except Exception:
			if len(x) == 0:
				raise EvaluationError('Can\'t run {} function with no arguments.'.format(name))
			elif len(x) == 1:
				formatted = calculator.errors.format_value(x[0])
				raise EvaluationError('Can\'t run {} function on value {}'.format(name, formatted))
			else:
				formatted = ', '.join(map(calculator.errors.format_value, x))
				raise EvaluationError('Can\'t run {} function on values ({})'.format(name, formatted))
	internal.__name__ = name
	return internal


def maybe_complex(f_real, f_complex):
	def internal(x):
		if isinstance(x, complex):
			return f_complex(x)
		return f_real(x)
	return except_math_error(internal)


# Changes a trig function to take degrees as its arguments
def fdeg(func):
	return lambda x : func(math.radians(x))


# Changes a trig function to produce degrees as its output
def adeg(func):
	return lambda x : math.degrees(func(x))


def m_choose(n, k):
	return calculator.operators.operator_division(
		calculator.operators.function_factorial(n),
		calculator.operators.operator_multiply(
			calculator.operators.function_factorial(k),
			calculator.operators.function_factorial(
				calculator.operators.operator_subtract(
					n,
					k
				)
			)
		)
	)


def is_function(x):
	return int(isinstance(x, Function) or isinstance(x, BuiltinFunction))


def is_real(x):
	return int(isinstance(x, int) or isinstance(x, float))


def is_complex(x):
	return int(isinstance(x, complex))



def array_length(x):
	if not isinstance(x, (Array, Interval, ListBase)):
		raise EvaluationError('Cannot get the length of non-array object')
	return len(x)


def array_splice(array, start, end):
	if not isinstance(array, Array):
		raise EvaluationError('Cannot splice non-array')
	if not isinstance(start, int) or not isinstance(end, int):
		raise EvaluationError('Non-integer indexes passed to splice')
	# Todo: Make this efficient
	return Array(array.items[start:end])


# Todo: Make this more efficient
def array_join(*items):
	if len(items) == 0:
		raise EvaluationError('Cannot join no arrays together.')
	result = []
	for i in items:
		if not isinstance(i, Array):
			raise EvaluationError('Cannot call join on non-array')
		result += i.items
	return Array(result)


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


# BUILTIN_MATH_FUNCTIONS = {
# 	# 'interval': lambda a, b: List(range(a, b)),
# 	'sin': maybe_complex(math.sin, cmath.sin),
# 	'cos': maybe_complex(math.cos, cmath.cos),
# 	'tan': maybe_complex(math.tan, cmath.tan),
# 	'sind': fdeg(math.sin),
# 	'cosd': fdeg(math.cos),
# 	'tand': fdeg(math.tan),
# 	'asin': maybe_complex(math.asin, cmath.asin),
# 	'acos': maybe_complex(math.acos, cmath.acos),
# 	'atan': maybe_complex(math.atan, cmath.atan),
# 	'asind': adeg(math.asin),
# 	'acosd': adeg(math.acos),
# 	'atand': adeg(math.atan),
# 	'sinh': maybe_complex(math.sinh, cmath.sinh),
# 	'cosh': maybe_complex(math.cosh, cmath.cosh),
# 	'tanh': maybe_complex(math.tanh, cmath.tanh),
# 	'asinh': maybe_complex(math.asinh, cmath.asinh),
# 	'acosh': maybe_complex(math.acosh, cmath.acosh),
# 	'atanh': maybe_complex(math.atanh, cmath.atanh),
# 	'deg': math.degrees,
# 	'rad': math.radians,
# 	'log': calculator.operators.function_logarithm,
# 	'ln': maybe_complex(math.log, cmath.log),
# 	'round': round,
# 	'int': int,
# 	'sqrt': lambda x : x ** 0.5,
# 	'gamma': lambda x: calculator.operators.function_factorial(x - 1),
# 	'gcd': calculator.operators.function_gcd,
# 	'lcm': calculator.operators.function_lcm,
# 	'choose': m_choose
# }

def mylog(e, b = 10):
	return sympy.log(e, b)

BUILTIN_FUNCTIONS = {
	# 'is_real': is_real,
	# 'is_complex': is_complex,
	'log': mylog,
	'ln': sympy.log,
	'is_function': is_function,
	'length': array_length,
	'join': array_join,
	'splice': array_splice,
	'expand': array_expand,
	# 'range': make_range,
	'int': sympy.Integer,
	'subs': lambda expr, symbol, value: expr.subs(symbol, value)
}

# FIXED_VALUES = {
# 	'e': math.e,
# 	'pi': math.pi,
# 	'π': math.pi,
# 	'tau': math.pi * 2,
# 	'τ': math.pi * 2,
# 	'i': 1j,
# 	'euler_gamma': 0.577215664901,
# 	'true': 1,
# 	'false': 0
# }


FIXED_VALUES = {
	'π': sympy.pi,
	'τ': sympy.pi * 2,
	'true': sympy.Integer(1),
	'false': sympy.Integer(0)
}


FIXED_VALUES_EXPORTABLE = {
	'π': math.pi,
	'τ': math.pi * 2,
	'pi': math.pi,
	'tau': math.pi * 2,
	'true': 1,
	'false': 0
}


EXTRACT_FROM_SYMPY = '''
	re im sign Abs arg conjugate 
	sin cos tan cot sec csc sinc asin acos atan acot asec acsc atan2 sinh cosh
	tanh coth sech csch asinh acosh atanh acoth asech acsch ceiling floor frac
	exp root sqrt pi E I gcd lcm gamma factorial
'''
# Things not used:
# polar_lift periodic_argument principal_branch diff integrate

ALL_SYMPY_CLASSES = tuple(sympy.core.all_classes)

def protect_sympy_function(func):
	def replacement(*args):
		for i in args:
			if not isinstance(i, ALL_SYMPY_CLASSES):
				raise TypeError
		return func(*args)
	return replacement


for i in EXTRACT_FROM_SYMPY.split():
	value = getattr(sympy, i)
	name = i.lower()
	if isinstance(value, (sympy.FunctionClass, types.FunctionType)):
		BUILTIN_FUNCTIONS[name] = protect_sympy_function(value)
	else:
		FIXED_VALUES[name] = value


# Code that is really useful to it's included by default
with open(os.path.join(os.path.dirname(__file__), 'library.c5')) as f:
	LIBRARY_CODE = f.read()


# CodeSegment.bytecodeify.btcfy__exact_item_hack = lambda s, n, _: s.push(n['value'])


def _assignment_code(name, value, add_terminal_byte=False):
	ast = {
		'#': 'assignment',
		'variable': {
			'string': name,
		},
		'value': {
			'#': '_exact_item_hack',
			'value': value
		}
	}
	return calculator.bytecode.ast_to_bytecode(ast, unsafe=True, add_terminal_byte=add_terminal_byte)


def strip_extra(t):
	if isinstance(t, (str, int)):
		return t
	if isinstance(t, list):
		return list(map(strip_extra, t))
	return {k:strip_extra(v) for k, v in t.items() if k != 'source'}


def findall(ast, tag):
	if isinstance(ast, list):
		for i in ast:
			yield from findall(i, tag)
	if isinstance(ast, dict):
		if ast.get('#') == tag:
			yield ast
		for k, v in ast.items():
			yield from findall(v, tag)


def lib_pieces():
	_, ast = parser.parse(LIBRARY_CODE, source_name='_system_library')
	definitions = {}
	for assignment in findall(ast, 'assignment'):
		name = assignment['variable']['string'].lower()
		definitions[name] = assignment
	return definitions


LIB_PIECES = lib_pieces()


def _prepare_runtime(exportable=False):
	if exportable:
		for name, value in FIXED_VALUES_EXPORTABLE.items():
			yield _assignment_code(name, value)
	else:
		for name, value in FIXED_VALUES.items():
			yield _assignment_code(name, value)
		for name, func in BUILTIN_FUNCTIONS.items():
			yield _assignment_code(name, BuiltinFunction(func, name))
	_, ast = parser.parse(LIBRARY_CODE, source_name='_system_library')
	yield calculator.bytecode.ast_to_bytecode(ast, unsafe=True)


@functools.lru_cache
def prepare_runtime(**kwargs):
	return list(_prepare_runtime(**kwargs))


def load_on_demand(name):
	if name in FIXED_VALUES:
		return _assignment_code(name, FIXED_VALUES[name], add_terminal_byte=True)
	if name in BUILTIN_FUNCTIONS:
		return _assignment_code(name, BuiltinFunction(BUILTIN_FUNCTIONS[name], name), add_terminal_byte=True)
	if name in LIB_PIECES:
		return calculator.bytecode.ast_to_bytecode(LIB_PIECES[name], unsafe=True, add_terminal_byte=True)
	return None


def wrap_simple(ast):
	builder = CodeBuilder()
	return wrap_with_runtime(builder, ast)
