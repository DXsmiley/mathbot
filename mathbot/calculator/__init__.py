import calculator.interpereter
import calculator.parser
import calculator.runtime
import calculator.bytecode

def calculate(equation, tick_limit = None):
	tokens, ast = calculator.parser.parse(equation)
	bytecode = calculator.runtime.wrap_simple(ast)
	interp = calculator.interpereter.Interpereter(bytecode)
	return interp.run(tick_limit = tick_limit)

async def calculate_async(equation, tick_limit = None):
	tokens, ast = calculator.parser.parse(equation)
	bytecode = calculator.runtime.wrap_simple(ast)
	interp = calculator.interpereter.Interpereter(bytecode)
	return await interp.run_async(tick_limit = tick_limit)