import argparse

import json
import asyncio
import traceback
import sys

from calculator.interpereter import Interpereter
import calculator.parser as parser
import calculator.bytecode as bytecode
import calculator.runtime as runtime
import calculator.errors as errors
from calculator.runtime import prepare_runtime
from calculator.blackbox import Terminal, format_error_place


def main():
	if len(sys.argv) == 1:
		interactive_terminal()
		return
	# Some options, gotta run file
	try:
		args = parse_arguments()
		filename = proc_filename(args.filename)
		sys.exit(run_file(filename))
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


def run_file(filename):
	code = open(filename).read()

	terminal = Terminal.new_blackbox_sync(
		allow_special_commands=False,
		yield_rate=1,
		trap_unknown_errors=False
	)

	output, worked, details = terminal.execute(code)
	print(output)

	return 0 if worked else 1


def interactive_terminal():
	terminal = Terminal.new_blackbox_sync(
		allow_special_commands=True,
		yield_rate=1,
		trap_unknown_errors=True
	)
	while True:
		try:
			line = input('> ')
		except (EOFError, KeyboardInterrupt):
			break
		if line in [':q', ':x', ':quit', ':exit']:
			break
		if line == '':
			continue
		try:
			output, worked, details = terminal.execute(line)
			print(output)
		except KeyboardInterrupt:
			print('Operation halted by keyboard interupt')

main()
