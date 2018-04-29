''' Calculator module

	This module is an implementation of a calculator,
	which is actually a turing-complete programming language.

	Go figure.

'''

import asyncio
import calculator.interpereter
import calculator.parser
import calculator.runtime
import calculator.bytecode
import calculator.errors
import calculator.blackbox

def calculate(equation, tick_limit=None, trace=False, use_runtime=True):
	''' Evaluate an expression '''
	interp = calculator.interpereter.Interpereter(trace=trace)
	builder = calculator.bytecode.Builder()
	# Setup the runtime
	if use_runtime:
		segment_runtime = runtime.prepare_runtime(builder)
		interp.run(segment=segment_runtime)
	# Run the actual program
	_, ast = calculator.parser.parse(equation)
	segment_program = builder.build(ast)
	return interp.run(segment=segment_program, tick_limit=tick_limit, error_if_exhausted=True)


async def calculate_async(equation):
	''' Evaluate an expression asyncronously '''
	_, ast = calculator.parser.parse(equation)
	bytecode = calculator.runtime.wrap_simple(ast)
	interp = calculator.interpereter.Interpereter(bytecode)
	return await interp.run_async()
