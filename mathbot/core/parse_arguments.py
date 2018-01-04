class InvalidArgumentNumber(Exception):
	pass


class InvalidArgumentType(Exception):
	pass


class InvalidGreedyConsumerArgument(Exception):
	pass


class InvalidFormatError(ValueError):
	pass


def remove_whitespace(stack):
	while len(stack) > 0 and stack[-1] in ' \t\n':
		stack.pop()


def eat_until(stack, terminal):
	string = ''
	while len(stack) > 0 and stack[-1] not in terminal:
		string += stack.pop()
	if len(stack) > 0:
		stack.pop()
	return string


def break_args(args):
	stack = list(args[::-1])
	result = []
	remove_whitespace(stack)
	while len(stack) > 0:
		if stack[-1] in '"\'':
			result.append(eat_until(stack, stack.pop()))
		else:
			result.append(eat_until(stack, ' \t\n'))
		remove_whitespace(stack)
	return result


def parse(format, argstring):
	# TODO: Support for '*' at the end of something
	if format == '*':
		return [argstring]
	elif format == '':
		if argstring.strip() != '':
			raise InvalidArgumentNumber
		return []
	else:
		args = break_args(argstring)[::-1]
		output = []
		format = format.split(' ')
		if len(args) < len(format):
			raise InvalidArgumentNumber
		if '*' not in format and len(args) != len(format):
			raise InvalidArgumentNumber
		for i, v in enumerate(format):
			if v == 'string':
				output.append(args.pop())
			elif v == 'integer':
				try:
					output.append(int(args.pop()))
				except ValueError:
					raise InvalidArgumentType
			elif v == '*':
				output.append(' '.join(args[::-1]))
				args = []
				if i != len(format) - 1:
					raise InvalidGreedyConsumerArgument
			else:
				raise InvalidFormatError('{} is not a valid argument format'.format(v))
		return output
