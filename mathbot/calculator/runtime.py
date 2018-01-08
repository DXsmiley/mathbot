# Bytecode that gets included with every program that runs.
# This contains a number of builtin functions and things.

import math
import cmath
import itertools
import os
import sympy
import types

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


def wrap_with_runtime(builder, my_ast, exportable=False, protect_globals=False):
	# ----- Declarations --------------------
	elnk = {'name': '_system_base', 'position': 0, 'code': '?'}
	s = builder.new_segment()
	if protect_globals:
		s.push(I.BEGIN_PROTECTED_GLOBAL_BLOCK)
	def assignment(name, value):
		s.push(I.CONSTANT, error = elnk)
		s.push(value)
		scope, depth, index = builder.globalscope.find_value(name)
		assert(scope == builder.globalscope)
		assert(depth == 0)
		s.push(I.ASSIGNMENT, error = elnk)
		s.push(index)
	def function(name, address, macro = False):
		s.push(I.FUNCTION_MACRO if macro else I.FUNCTION_NORMAL, error = elnk)
		s.push(Pointer(address))
		scope, depth, index = builder.globalscope.find_value(name)
		assert(scope == builder.globalscope)
		assert(depth == 0)
		s.push(I.ASSIGNMENT, error = elnk)
		s.push(index)
	# Mathematical constants
	if exportable:
		for name, value in FIXED_VALUES_EXPORTABLE.items():
			assignment(name, value)
	else:
		for name, value in FIXED_VALUES.items():
			assignment(name, value)
	# Builtin functions
	if not exportable:
		# for name, func in BUILTIN_MATH_FUNCTIONS.items():
		# 	wrapped = except_math_error(func, name)
		# 	assignment(name, BuiltinFunction(wrapped, name))
		for name, func in BUILTIN_FUNCTIONS.items():
			assignment(name, BuiltinFunction(func, name))
	# The essential things
	# _, ast = parser.parse(BOILER_CODE)
	# builder.bytecodeify(ast, unsafe = True)
	_, ast = parser.parse(LIBRARY_CODE, source_name = '_system_library')
	builder.bytecodeify(ast, unsafe = True)
	# ----- User Code -----------------------
	if my_ast is not None:
		builder.bytecodeify(my_ast)
	if protect_globals:
		builder.new_segment().push(I.END_PROTECTED_GLOBAL_BLOCK, error = elnk)
	builder.new_segment().push(I.END, error = elnk)
	# ----- Return the resulting bytecode -
	return builder.dump()


def wrap_simple(ast):
	builder = CodeBuilder()
	return wrap_with_runtime(builder, ast)
