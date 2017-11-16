import argparse

import json
import asyncio
import traceback
import sys

import calculator
from calculator.interpereter import Interpereter
import calculator.parser as parser
import calculator.bytecode as bytecode
import calculator.runtime as runtime
import calculator.errors as errors
from calculator.runtime import wrap_with_runtime


def main():
	if len(sys.argv) == 1:
		interactive_terminal()
		return
	# Some options, gotta run file
	try:
		args = parse_arguments()
		filename = proc_filename(args.filename)
		code = open(filename).read()
		tokens, ast = parser.parse(code, source_name = filename)
		btc = wrap_with_runtime(bytecode.CodeBuilder(), ast, exportable = args.compile)
		if args.compile:
			print(btc.dump())
			return
		interpereter = Interpereter(btc, trace = args.trace)
		result = interpereter.run()
		print(result)
	except parser.ParseFailed as e:
		print(format_error_place(code, e.position))


def parse_arguments():
	parser = argparse.ArgumentParser()
	parser.add_argument('filename', help = 'The filename of the program to run')
	action = parser.add_mutually_exclusive_group()
	action.add_argument('-t', '--trace', action = 'store_true', help = 'Display details of the program as it is running')
	action.add_argument('-c', '--compile', action = 'store_true', help = 'Dumps the bytecode of the program rather than running it')
	return parser.parse_args()


def proc_filename(filename):
    if filename[0] == '+':
        return './calculator/scripts/' + filename[1:] + '.c5'
    return filename


def print_token_parse_caret(to):
	print(' '.join(to.tokens))
	print((sum(map(len, to.tokens[:to.rightmost])) + to.rightmost) * ' ' + '^')


def interactive_terminal():

	terminal = calculator.blackbox.Terminal(allow_special_commands = True)

	while True:
		line = input('> ')
		if line == '':
			break
		output, worked = terminal.execute(line)
		print(output)

main()
