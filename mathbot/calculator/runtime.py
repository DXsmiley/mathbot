# Bytecode that gets included with every program that runs.
# This contains a number of builtin functions and things.

import math

from calculator.bytecode import *


def wrap_with_runtime(builder, my_ast):
	# ----- Declarations --------------------
	s = builder.new_segment()
	# Mathematical constants
	s.push(I.CONSTANT)
	s.push(math.e)
	s.push(I.ASSIGNMENT)
	s.push('e')
	s.push(I.CONSTANT)
	s.push(math.pi)
	s.push(I.ASSIGNMENT)
	s.push('pi')
	# Declare if statement
	if_statement = Destination()
	s.push(I.FUNCTION_MACRO)
	s.push(Pointer(if_statement))
	s.push(I.ASSIGNMENT)
	s.push('if')
	# ----- User Code -----------------------
	if my_ast is not None:
		builder.bytecodeify(my_ast)
	else:
		s.push(I.END)
	# ----- Definitions ---------------------
	s = builder.new_segment()
	# Define if statement
	s.push(if_statement)
	# Number of arguments and their names
	s.push(3)
	s.push('_a')
	s.push('_b')
	s.push('_c')
	# Determine the value of the condition
	s.push(I.WORD)
	s.push('_a')
	s.push(I.ARG_LIST_END)
	s.push(0)
	# If the result is false, jump to the end of the function.
	s.push(I.JUMP_IF_FALSE)
	false_landing = Destination()
	s.push(Pointer(false_landing))
	# Return the 'true' result
	s.push(I.WORD)
	s.push('_b')
	s.push(I.ARG_LIST_END)
	s.push(0)
	s.push(I.RETURN)
	# Return the 'false' result
	s.push(false_landing)
	s.push(I.WORD)
	s.push('_c')
	s.push(I.ARG_LIST_END)
	s.push(0)
	s.push(I.RETURN)
	# ----- Return the resulting bytecode -
	return builder.dump()
