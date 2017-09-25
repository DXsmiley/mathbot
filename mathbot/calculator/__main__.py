# Successfull burning attack: f = (x, h) -> if (h - 40, f(x * 2, h + 1) + f(x * 2 + 1, h + 1), 0)



import json
import asyncio
import traceback
import calculator.calculator as c
import sys
import calculator.attempt6


def run_with_timeout(future, timeout = None):
	loop = asyncio.get_event_loop()
	future = asyncio.wait_for(future, timeout = timeout)
	return loop.run_until_complete(future)


def print_token_parse_caret(to):
	print(' '.join(to.tokens))
	print((sum(map(len, to.tokens[:to.rightmost])) + to.rightmost) * ' ' + '^')

ERROR_TEMPLATE = '''\
{prev}
{cur}
{carat}
{next}
'''


def format_parse_error(message, string, position):
	lines = [' '] + string.split('\n') + [' ']
	line = 1
	while position > len(lines[line]):
		position -= len(lines[line]) + 1
		line += 1
	length = len(string)
	return ERROR_TEMPLATE.format(
		prev = lines[line - 1],
		cur = lines[line],
		next = lines[line + 1],
		carat = ' ' * (position - 1) + '^'
	)


if __name__ == '__main__':

	if len(sys.argv) == 1:

		show_tree = False
		show_parsepoint = False
		user_scope = c.new_scope()

		while True:
			line = input('> ')
			if line == '':
				break
			elif line == ':tree':
				show_tree = not show_tree
			elif line == ':parsepoint':
				show_parsepoint = not show_parsepoint
			else:
				try:
					# to, result = c.parse(c.GRAMMAR, line, check_ambiguity = True)
					to, result = calculator.attempt6.parse(line)
				except c.TokenizationFailed as e:
					print('Failed to parse equation, unexpected symbol:')
					print(e.string)
					print(' ' * e.consumed + '^')
				except c.ParseFailed as e:
					print('Failed to parse equation, invalid syntax:')
					print(e.string)
					print(' ' * e.consumed + '^')
				else:
					if result is None:
						print('Failed to parse the equation:')
						print_token_parse_caret(to)
					else:
						if show_parsepoint:
							print_token_parse_caret(to)
						if show_tree:
							print(json.dumps(result, indent = 4))
						try:
							future = c.evaluate(result, user_scope, limits = {'warnings': True})
							warnings, result = run_with_timeout(future, 5)
							for i in warnings:
								print(i)
							print(result)
						except asyncio.TimeoutError:
							print('Function took too long to compute.')
						except Exception as e:
							print('Error:', e)
							traceback.print_exc()
						user_scope.clear_cache()

	elif len(sys.argv) == 2:

		filename = sys.argv[1]
		if filename[0] == '+':
			filename = './calculator/scripts/' + filename[1:] + '.c5'
		code = open(filename).read()
		try:
			print(c.calculate(code))
		except calculator.attempt6.ParseFailed as e:
			print(format_parse_error('error', code, e.position))

	else:

		print('???')
