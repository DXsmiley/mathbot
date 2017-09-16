# Bytecode that gets included with every program that runs.
# This contains a number of builtin functions and things.

import math

from calculator.bytecode import *
from calculator.functions import *
import calculator.operators as operators


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
		s.push(I.ASSIGNMENT)
		s.push(name)
	# Mathematical constants
	assignment('e', math.e)
	assignment('pi', math.pi)
	assignment('π', math.pi)
	assignment('true', 1)
	assignment('false', 0)
	# Builtin functions
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
	# Declare if statement : if (condition, true_case, false_case)
	if_statement = Destination()
	s.push(I.FUNCTION_MACRO)
	s.push(Pointer(if_statement))
	s.push(I.ASSIGNMENT)
	s.push('if')
	# Declare reduce function : reduce (function, array)
	# reduce = Destination()
	# s.push(I.FUNCTION_NORMAL)
	# s.push(Pointer(reduce))
	# s.push(I.ASSIGNMENT)
	# s.push('reduce')
	# ----- User Code -----------------------
	if my_ast is not None:
		builder.bytecodeify(my_ast)
	else:
		s.push(I.END)
	# ----- Definitions ---------------------
	s = builder.new_segment()
	# ----- Define if statement -------------
	s.push(if_statement)
	# Number of arguments and their names
	s.push(3)
	s.push('_a')
	s.push('_b')
	s.push('_c')
	s.push(0) # Not variadic
	# Determine the value of the condition
	s.push(I.WORD)
	s.push('_a')
	s.push(I.ARG_LIST_END)
	s.push(0)
	s.push(I.STORE_IN_CACHE)
	# If the result is false, jump to the end of the function.
	s.push(I.JUMP_IF_FALSE)
	false_landing = Destination()
	s.push(Pointer(false_landing))
	# Return the 'true' result
	s.push(I.WORD)
	s.push('_b')
	s.push(I.ARG_LIST_END)
	s.push(0)
	s.push(I.STORE_IN_CACHE)
	s.push(I.RETURN)
	# Return the 'false' result
	s.push(false_landing)
	s.push(I.WORD)
	s.push('_c')
	s.push(I.ARG_LIST_END)
	s.push(0)
	s.push(I.STORE_IN_CACHE)
	s.push(I.RETURN)
	# ----- Define reduce function --------
	# s.push(reduce)
	# s.push(2)
	# s.push('_f')
	# s.push('_a')

	# ----- Return the resulting bytecode -
	return builder.dump()
