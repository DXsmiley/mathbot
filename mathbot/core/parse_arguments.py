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


def _parse_format_spec(format_string):
	return list(map(_parse_format_spec_item, format_string.split(' ')))


def _parse_format_spec_item(spec_item):
	parts = spec_item.split('|')
	typ = parts[0]
	manip = _create_manipluation_function(parts[1:])
	return typ, manip


def _create_manipluation_function(parts):
	if not parts:
		return _passthrough
	try:
		functions = list(map(MANIPLATOR_FUNCTIONS.__getitem__, parts))
	except KeyError as err:
		raise ValueError(f'{err} is not a valid manipulator function')
	def _internal(value):
		for i in functions:
			value = i(value)
		return value
	return _internal


def _passthrough(value):
	return value


MANIPLATOR_FUNCTIONS = {
	'lower': str.lower,
	'upper': str.upper
}


def iter_mark_last(iterable):
	''' Iterates over an iterable, marking the last item in the sequence. '''
	try:
		current = next(iterable)
	except StopIteration:
		return
	complete = False
	while not complete:
		try:
			lookahead = next(iterable)
		except StopIteration:
			complete = True
		yield complete, current
		if not complete:
			current = lookahead


def parse(format_string, argstring):
	if format_string.startswith('*'):
		_, manip = _parse_format_spec_item(argstring)
		return [manip(argstring)]
	elif format_string == '':
		if argstring.strip() != '':
			raise InvalidArgumentNumber
		return []
	else:
		args = break_args(argstring)
		output = []
		format_spec = _parse_format_spec(format_string)
		if len(args) < len(format_spec):
			raise InvalidArgumentNumber
		if '*' not in format_string and len(args) != len(format_spec):
			raise InvalidArgumentNumber
		for is_last, ((typ, manip), arg) in iter_mark_last(zip(format_spec, args)):
			if typ == 'string':
				output.append(manip(arg))
			elif typ == 'integer':
				try:
					output.append(manip(int(arg)))
				except ValueError:
					raise InvalidArgumentType
			elif typ == '*':
				pieces = args[len(format_spec) - 1:]
				output.append(manip(' '.join(pieces)))
				if not is_last:
					raise InvalidGreedyConsumerArgument
			else:
				raise InvalidFormatError(f'{typ} is not a valid argument format')
		return output
