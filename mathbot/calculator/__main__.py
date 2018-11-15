import calculator.tokenizer as tokenizer
import calculator.parser_new as parser_new
import calculator.combinator as combinator
import calculator.syntax_trees as syntax_trees
import sys
from calculator.errors import TokenizationFailed, make_source_marker_at_location
from .errors import EvaluationError
import traceback


sys.setrecursionlimit(6000)


def runline(program, line):
	try:
		tokens = tokenizer.tokenize(line)
	except TokenizationFailed as e:
		print(e)
		# print(make_source_marker_at_location(e.source, e.location))
		return
	parsed = parser_new.program.run(tokens)
	if not parsed:
		t = parsed.tokens.first_token
		print(f'Problem during parsing: {parsed.value}')
		print(make_source_marker_at_location(t.source, t.location))
		return
	ast = combinator.postprocess(parsed.value)
	program.merge_definitions(ast.bindings, protection_level=0)
	try:
		output = program.eval_expressions(ast.expressions)
		for i in output:
			print(i)
	except EvaluationError as e:
		print(e)
	except Exception as e:
		print('General exception escaped evaluator')
		traceback.print_exc()


def main():
	prog = syntax_trees.MergeableProgram()
	while True:
		line = input('> ')
		if line == '':
			continue
		if line in [':x', ':exit', ':q', ':quit']:
			break
		runline(prog, line)
	

if __name__ == '__main__':
	main()
