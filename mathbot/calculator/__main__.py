import calculator.tokenizer as tokenizer
import calculator.parser_new as parser_new
import calculator.combinator as combinator
import calculator.syntax_trees as syntax_trees
from calculator.errors import TokenizationFailed, make_source_marker_at_location


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
	prog.merge_definitions(ast.bindings)
	output = program.eval_expressions(ast.expressions)
	for i in output:
		print(i)


if __name__ == '__main__':
	prog = syntax_trees.MergeableProgram()
	while True:
		line = input('> ')
		if line == '':
			continue
		if line in [':x', ':exit', ':q', ':quit']:
			break
		runline(prog, line)

