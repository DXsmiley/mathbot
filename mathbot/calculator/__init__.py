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

def calculate(equation, tick_limit=None):
	''' Evaluate an expression '''
	_, ast = calculator.parser.parse(equation)
	bytecode = calculator.runtime.wrap_simple(ast)
	interp = calculator.interpereter.Interpereter(bytecode)
	return interp.run(tick_limit=tick_limit, error_if_exhausted=True, expect_complete=True)

async def calculate_async(equation):
	''' Evaluate an expression asyncronously '''
	_, ast = calculator.parser.parse(equation)
	bytecode = calculator.runtime.wrap_simple(ast)
	interp = calculator.interpereter.Interpereter(bytecode)
	return await interp.run_async()
