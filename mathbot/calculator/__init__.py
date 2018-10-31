''' Calculator module

	This module is an implementation of a calculator,
	which is actually a turing-complete programming language.

	Go figure.

'''

# import asyncio
# import calculator.interpereter
# import calculator.parser
# import calculator.runtime
# import calculator.bytecode
# import calculator.errors
# import calculator.blackbox

# def calculate(equation, tick_limit=None, trace=False, use_runtime=True):
# 	''' Evaluate an expression '''
# 	interp = calculator.interpereter.Interpereter(trace=trace)
# 	builder = calculator.bytecode.Builder()
# 	# Setup the runtime
# 	if use_runtime:
# 		segment_runtime = runtime.prepare_runtime(builder)
# 		interp.run(segment=segment_runtime)
# 	# Run the actual program
# 	_, ast = calculator.parser.parse(equation)
# 	segment_program = builder.build(ast)
# 	return interp.run(segment=segment_program, tick_limit=tick_limit, error_if_exhausted=True)


# async def calculate_async(equation):
# 	''' Evaluate an expression asyncronously '''
# 	_, ast = calculator.parser.parse(equation)
# 	bytecode = calculator.runtime.wrap_simple(ast)
# 	interp = calculator.interpereter.Interpereter(bytecode)
# 	return await interp.run_async()

import calculator.tokenizer as tokenizer
import calculator.parser_new as parser_new
import calculator.combinator as combinator
import calculator.syntax_trees as syntax_trees
import calculator.runtime as runtime
from calculator.errors import TokenizationFailed, make_source_marker_at_location

def source_to_ast(source):
	tokens = tokenizer.tokenize(source)
	parsed = parser_new.program.run(tokens)
	if not parsed:
		raise Exception('Parsing failed')
	return combinator.postprocess(parsed.value)

def calculate(equation, *, tick_limit=None, use_runtime=False, trace=False):
	prog = syntax_trees.MergeableProgram()
	prog.merge_definitions(runtime.prepare_runtime().bindings, protection_level=2)
	ast = source_to_ast(equation)
	prog.merge_definitions(ast.bindings, protection_level=0)
	# output = ast.fulleval(syntax_trees.Environment(None, {}))
	output = prog.eval_expressions(ast.expressions)
	return output[-1] if output else None
