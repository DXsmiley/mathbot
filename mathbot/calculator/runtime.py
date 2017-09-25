# Bytecode that gets included with every program that runs.
# This contains a number of builtin functions and things.

import math

from calculator.bytecode import *
from calculator.functions import *
import calculator.operators as operators
import calculator.parser as parser


# This looks weird but it works because the functions on the inside
# get optimised out
BOILER_CODE = parser.parse('''
array = (a.) -> a,
if = (c, t, f) ~> if(c(), t(), f()),
map = (f, a) -> map(f, a),
reduce = (f, a) -> reduce(f, a)
''')[1]


def is_function(x):
	return int(isinstance(x, Function) or isinstance(x, BuiltinFunction))


def is_real(x):
	return int(isinstance(x, int) or isinstance(x, float))


def is_complex(x):
	return int(isinstance(x, complex))


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
	# Builtin functions
	assignment('e', math.e)
	assignment('pi', math.pi)
	assignment('π', math.pi)
	assignment('true', 1)
	assignment('false', 0)
	if not exportable:
		assignment('round', BuiltinFunction(round))
		assignment('sin', BuiltinFunction(math.sin))
		assignment('cos', BuiltinFunction(math.cos))
		assignment('log', BuiltinFunction(math.log))
		assignment('length', BuiltinFunction(len))
		assignment('expand', BuiltinFunction(Expanded))
		assignment('is_function', BuiltinFunction(is_function))
		assignment('is_real', BuiltinFunction(is_real))
		assignment('is_complex', BuiltinFunction(is_complex))
		assignment('gcd', BuiltinFunction(operators.function_gcd))
		assignment('lcm', BuiltinFunction(operators.function_lcm))
		assignment('log', BuiltinFunction(operators.function_logarithm))
		assignment('ln', BuiltinFunction(math.log))
		assignment('gamma', BuiltinFunction(lambda x: operators.function_factorial(x - 1)))
	# assignment('')
	builder.bytecodeify(BOILER_CODE)
	# ----- User Code -----------------------
	if my_ast is not None:
		builder.bytecodeify(my_ast)
	builder.new_segment().push(I.END)
	# ----- Return the resulting bytecode -
	return builder.dump()

def wrap_simple(ast):
	builder = CodeBuilder()
	return wrap_with_runtime(builder, ast)