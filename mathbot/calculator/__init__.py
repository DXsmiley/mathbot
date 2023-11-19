''' Calculator module

	This module is an implementation of a calculator,
	which is actually a turing-complete programming language.

	Go figure.

'''

from . import interpereter
from . import parser
from . import runtime
from . import bytecode
from . import functions
from . import errors


def calculate(equation, tick_limit=None, trace=False, use_runtime=True):
	''' Evaluate an expression '''
	interp = interpereter.Interpereter(trace=trace)
	builder = bytecode.Builder()
	# Setup the runtime
	if use_runtime:
		segment_runtime = runtime.prepare_runtime(builder)
		interp.run(segment=segment_runtime)
	# Run the actual program
	_, ast = parser.parse(equation)
	segment_program = builder.build(ast)
	return interp.run(segment=segment_program, tick_limit=tick_limit, error_if_exhausted=True)


async def calculate_async(equation):
	''' Evaluate an expression asyncronously '''
	_, ast = parser.parse(equation)
	bc = runtime.wrap_simple(ast)
	interp = interpereter.Interpereter(bc)
	return await interp.run_async()
