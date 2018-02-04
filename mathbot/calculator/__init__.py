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

def calculate(equation, tick_limit=None, trace=False):
	''' Evaluate an expression '''
	_, ast = calculator.parser.parse(equation)
	runtime = calculator.runtime.prepare_runtime()
	program = calculator.bytecode.ast_to_bytecode(ast)
	linker = calculator.bytecode.Linker()
	runtime_location = linker.add_segments(runtime)
	program_location = linker.add_segment(program)
	interp = calculator.interpereter.Interpereter(linker.constructed(), trace=trace)
	interp.run(start_address=runtime_location)
	return interp.run(start_address=program_location, tick_limit=tick_limit, error_if_exhausted=True)

async def calculate_async(equation):
	''' Evaluate an expression asyncronously '''
	_, ast = calculator.parser.parse(equation)
	bytecode = calculator.runtime.wrap_simple(ast)
	interp = calculator.interpereter.Interpereter(bytecode)
	return await interp.run_async()
