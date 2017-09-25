import argparse

import json
import asyncio
import traceback
import sys

from calculator.interpereter import Interpereter
import calculator.parser as parser
import calculator.bytecode as bytecode
import calculator.runtime as runtime
from calculator.runtime import wrap_with_runtime


ERROR_TEMPLATE = '''\
{prev}
{cur}
{carat}
{next}
'''


def main():
	if len(sys.argv) == 1:
		interactive_terminal()
		return
	# Some options, gotta run file
	try:
		args = parse_arguments()
		filename = proc_filename(args.filename)
		code = open(filename).read()
		tokens, ast = parser.parse(code)
		btc = wrap_with_runtime(bytecode.CodeBuilder(), ast, exportable = True)
		if args.compile:
			print(bytecode.stringify(btc))
			return
		interpereter = Interpereter(btc, trace = args.trace)
		result = interpereter.run()
		print(result)
	except parser.ParseFailed as e:
		print(format_parse_error('error', code, e.position))


def parse_arguments():
	parser = argparse.ArgumentParser()
	parser.add_argument('filename', help = 'The filename of the program to run')
	action = parser.add_mutually_exclusive_group()
	action.add_argument('-t', '--trace', action = 'store_true', help = 'Display details of the program as it is running')
	action.add_argument('-c', '--compile', action = 'store_true', help = 'Dumps the bytecode of the program rather than running it')
	return parser.parse_args()


def run_with_timeout(future, timeout = None):
	loop = asyncio.get_event_loop()
	future = asyncio.wait_for(future, timeout = timeout)
	return loop.run_until_complete(future)


def print_token_parse_caret(to):
	print(' '.join(to.tokens))
	print((sum(map(len, to.tokens[:to.rightmost])) + to.rightmost) * ' ' + '^')


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


def proc_filename(filename):
	if filename[0] == '+':
		return './calculator/scripts/' + filename[1:] + '.c5'
	return filename


def interactive_terminal():

	show_tree = False
	show_parsepoint = False
	builder = bytecode.CodeBuilder()
	runtime = wrap_with_runtime(builder, None)
	interpereter = Interpereter(runtime, builder = builder)
	interpereter.run()

	while True:
		line = input('> ')
		if line == '':
			break
		elif line == ':tree':
			show_tree = not show_tree
		elif line == ':parsepoint':
			show_parsepoint = not show_parsepoint
		elif line == ':trace':
			interpereter.trace = not interpereter.trace
		else:
			tokens, ast = parser.parse(line)
			ast = {'#': 'program', 'items': [ast, {'#': 'end'}]}
			# print(json.dumps(ast, indent = 4))
			interpereter.prepare_extra_code({
				'#': 'program',
				'items': [ast]
			})
			# for index, byte in enumerate(bytes):
			# 	print('{:3d} - {}'.format(index, byte))
			print(run_with_timeout(interpereter.run_async(), 5))


main()