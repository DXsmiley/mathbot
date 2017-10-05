# Bytecode that gets included with every program that runs.
# This contains a number of builtin functions and things.

import math
import cmath
import itertools
import os

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
	if not isinstance(x, (Array, Interval)):
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
		if not isinstance(i, Array):
			raise EvaluationError('Cannot expand non-array')
	return Expanded(arrays)


def make_range(start, end):
	if not isinstance(start, int):
		raise EvaluationError('Cannot create range on non-int')
	if not isinstance(end, int):
		raise EvaluationError('Cannot create range on non-int')
	if end < start:
		raise EvaluationError('Cannot create backwards ranges')
	return Interval(start, 1, end - start)


BUILTIN_MATH_FUNCTIONS = {
	# 'interval': lambda a, b: List(range(a, b)),
	'sin': maybe_complex(math.sin, cmath.sin),
	'cos': maybe_complex(math.cos, cmath.cos),
	'tan': maybe_complex(math.tan, cmath.tan),
	'sind': fdeg(math.sin),
	'cosd': fdeg(math.cos),
	'tand': fdeg(math.tan),
	'asin': maybe_complex(math.asin, cmath.asin),
	'acos': maybe_complex(math.acos, cmath.acos),
	'atan': maybe_complex(math.atan, cmath.atan),
	'asind': adeg(math.asin),
	'acosd': adeg(math.acos),
	'atand': adeg(math.atan),
	'sinh': maybe_complex(math.sinh, cmath.sinh),
	'cosh': maybe_complex(math.cosh, cmath.cosh),
	'tanh': maybe_complex(math.tanh, cmath.tanh),
	'asinh': maybe_complex(math.asinh, cmath.asinh),
	'acosh': maybe_complex(math.acosh, cmath.acosh),
	'atanh': maybe_complex(math.atanh, cmath.atanh),
	'deg': math.degrees,
	'rad': math.radians,
	'log': calculator.operators.function_logarithm,
	'ln': maybe_complex(math.log, cmath.log),
	'round': round,
	'int': int,
	'sqrt': lambda x : x ** 0.5,
	'gamma': lambda x: calculator.operators.function_factorial(x - 1),
	'gcd': calculator.operators.function_gcd,
	'lcm': calculator.operators.function_lcm,
	'choose': m_choose
}

BUILTIN_FUNCTIONS = {
	'is_real': is_real,
	'is_complex': is_complex,
	'is_function': is_function,
	'length': array_length,
	'join': array_join,
	'splice': array_splice,
	'expand': array_expand,
	'im': lambda x: x.imag,
	're': lambda x: x.real,
	'range': make_range
}


FIXED_VALUES = {
	'e': math.e,
	'pi': math.pi,
	'π': math.pi,
	'i': 1j,
	'euler_gamma': 0.577215664901,
	'tau': math.pi * 2,
	'true': 1,
	'false': 0
}


# This looks weird but it works because the functions on the inside get optimised out
BOILER_CODE = '''
if = (c, t, f) ~> if(c(), t(), f()),
map = (f, a) -> map(f, a),
reduce = (f, a) -> reduce(f, a),
filter = (f, a) -> filter(f, a)
'''


# Code that is really useful to it's included by default
with open(os.path.join(os.path.dirname(__file__), 'library.c5')) as f:
	LIBRARY_CODE = f.read()


def wrap_with_runtime(builder, my_ast, exportable = False):
	# ----- Declarations --------------------
	s = builder.new_segment()
	def assignment(name, value):
		s.push(I.CONSTANT)
		s.push(value)
		scope, depth, index = builder.globalscope.find_value(name)
		assert(scope == builder.globalscope)
		assert(depth == 0)
		s.push(I.ASSIGNMENT)
		s.push(index)
	def function(name, address, macro = False):
		s.push(I.FUNCTION_MACRO if macro else I.FUNCTION_NORMAL)
		s.push(Pointer(address))
		scope, depth, index = builder.globalscope.find_value(name)
		assert(scope == builder.globalscope)
		assert(depth == 0)
		s.push(I.ASSIGNMENT)
		s.push(index)
	# Mathematical constants
	for name, value in FIXED_VALUES.items():
		assignment(name, value)
	# Builtin functions
	if not exportable:
		for name, func in BUILTIN_MATH_FUNCTIONS.items():
			wrapped = except_math_error(func, name)
			assignment(name, BuiltinFunction(wrapped, name))
		for name, func in BUILTIN_FUNCTIONS.items():
			assignment(name, BuiltinFunction(func, name))
	# The essential things
	_, ast = parser.parse(BOILER_CODE)
	builder.bytecodeify(ast, unsafe = True)
	_, ast = parser.parse(LIBRARY_CODE)
	builder.bytecodeify(ast)
	# ----- User Code -----------------------
	if my_ast is not None:
		builder.bytecodeify(my_ast)
	builder.new_segment().push(I.END)
	# ----- Return the resulting bytecode -
	return builder.dump()


def wrap_simple(ast):
	builder = CodeBuilder()
	return wrap_with_runtime(builder, ast)
