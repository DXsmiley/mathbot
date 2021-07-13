import json
import re
import enum


class DelimitedBinding(enum.Enum):
	DONT_PROCESS     = 0
	LEFT_FIRST       = 1
	RIGHT_FIRST      = 2
	DROP_AND_FLATTEN = 3


class BracketType(enum.Enum):
	NONE   = 0
	ROUND  = 1
	SQUARE = 2
	CURLY  = 3


class BracketDirection(enum.Enum):
	LEFT = 0
	RIGHT = 1


bracket_type = lambda x: {
	'(': BracketType.ROUND,
	')': BracketType.ROUND,
	'[': BracketType.SQUARE,
	']': BracketType.SQUARE,
	'{': BracketType.CURLY,
	'}': BracketType.CURLY	
}.get(x, BracketType.NONE)


bracket_direction = lambda x: {
	'(': BracketDirection.LEFT,
	')': BracketDirection.RIGHT,
	'[': BracketDirection.LEFT,
	']': BracketDirection.RIGHT,
	'{': BracketDirection.LEFT,
	'}': BracketDirection.RIGHT	
}.get(x)


class ParseFailed(Exception):

	details = ''

	def __init__(self, *args):
		raise NotImplementedError("Should not be creating ParseFailed exceptions directly")

	def __str__(self):
		if self.details == '':
			return 'Failed to parse token at position {}'.format(self.position)
		return 'Failed to parse token at position {} : {}'.format(self.position, self.details)


class ParseFailedBlock(ParseFailed):

	def __init__(self, block):
		self.position = block.root.get_error_location()


class UnableToFinishParsing(ParseFailedBlock): pass
class UnexpectedLackOfToken(ParseFailedBlock): pass
class DeprecatedSyntax(ParseFailedBlock): pass


class ImbalancedBraces(ParseFailed):

	details = 'Imbalanced braces'

	def __init__(self, token):
		self.position = token['position']


class TokenizationFailed(Exception):

	def __init__(self, position):
		self.position = position


class TokenRoot:

	''' Class that contains a list of tokens '''

	def __init__(self, string, original_tokens, nested_tokens):
		self.string = string
		self.rightmost = -1
		self.original_tokens = original_tokens
		self.tokens = self.process_nested_tokens(nested_tokens)

	def update_rightmost(self, position):
		self.rightmost = max(self.rightmost, position)

	def process_nested_tokens(self, tokens):
		first = tokens.pop(0)
		last = tokens.pop()
		for i in range(len(tokens)):
			if isinstance(tokens[i], list):
				tokens[i] = self.process_nested_tokens(tokens[i])
		return TokenBlock(self, tokens, (first, last))

	def get_error_location(self):
		place = self.rightmost + 1
		# print(place)
		# for i, v in enumerate(self.original_tokens):
		# 	print('>>>' if i == place else '   ', v)
		return self.original_tokens[place]['position']


class TokenBlock:

	def __init__(self, root, values, edge_tokens):
		self.place = 0
		self.values = values
		self.root = root
		self.edge_tokens = edge_tokens
		self.edge_type = bracket_type(edge_tokens[0]['string'])

	@property
	def edge_start(self):
	    return self.edge_tokens[0]

	@property
	def edge_end(self):
	    return self.edge_tokens[1]

	def eat_details(self):
		self.place += 1
		token = self.values[self.place - 1]
		if not isinstance(token, TokenBlock):
			self.root.update_rightmost(token['index'])
		return token

	def details(self, index = 0):
		if self.place + index < len(self.values):
			return self.values[self.place + index]

	def peek(self, index, *valids):
		if TokenBlock in valids:
			print('TokenBlock is no longer a valid argument to TokenBlock.peek!')
		if self.place + index < len(self.values):
			t = self.values[self.place + index]
			if isinstance(t, TokenBlock):
				return t.edge_type in valids or TokenBlock in valids
			elif isinstance(t, dict):
				return t['#'] in valids

	def peek_sequence(self, index, *sequence):
		for offset, item in enumerate(sequence):
			if not self.peek(index + offset, item):
				return False
		return True

	def peek_string(self, index, *valids):
		if self.place + index < len(self.values):
			t = self.values[self.place + index]
			if isinstance(t, dict):
				return t['string'] in valids

	def peek_and_eat(self, index, *valids):
		assert index == 0
		if self.peek(index, *valids):
			return self.eat_details()


	def expect(self, index, *valids):
		r = self.peek(index, *valids)
		if r is None:
			raise UnableToFinishParsing(tokens)
		return r

	def is_complete(self):
		return self.place >= len(self.values)


def ensure_completed(function, tokens):
	result = function(tokens)
	if not tokens.is_complete():
		raise UnableToFinishParsing(tokens)
	return result


def expect(tokens, rule):
	result = rule(tokens)
	if result is None:
		raise UnableToFinishParsing(tokens)
	return result


def eat_delimited(subrule, delimiters, binding, type, allow_nothing = False, always_package = False):

	if not isinstance(binding, DelimitedBinding):
		raise ValueError('{} is not a valid rule for binding'.format(binding))

	def internal(tokens):
		listing = []
		if tokens.is_complete():
			if not allow_nothing:
				raise UnexpectedLackOfToken(tokens)
		else:
			listing = [expect(tokens, subrule)]
		while tokens.peek(0, *delimiters):
			listing.append(tokens.eat_details())
			listing.append(expect(tokens, subrule))
		if len(listing) == 1 and not always_package:
			return listing[0]
		if binding == DelimitedBinding.DONT_PROCESS:
			return {
				'#': type,
				'items': listing
			}
		elif binding == DelimitedBinding.DROP_AND_FLATTEN:
			return {
				'#': type,
				'items': listing[::2]
			}
		elif binding == DelimitedBinding.LEFT_FIRST:
			listing = list(listing[::-1])
			value = listing.pop()
			while listing:
				delimiter = listing.pop()
				right = listing.pop()
				value = {
					'#': type,
					'operator': delimiter['string'],
					'left': value,
					'right': right,
					'token': delimiter
				}
			return value
		elif binding == DelimitedBinding.RIGHT_FIRST:
			value = listing.pop()
			while listing:
				delimiter = listing.pop()
				left = listing.pop()
				value = {
					'#': type,
					'operator': delimiter['string'],
					'left': left,
					'right': value,
					'token': delimiter
				}
			return value

	internal.__name__ = 'eat_delimited___' + type
	return internal


def eat_optionally_delimited(subrule, delimiters, binding, type, allow_nothing = False, always_package = False):

	if not isinstance(binding, DelimitedBinding):
		raise ValueError('{} is not a valid rule for binding'.format(binding))

	def internal(tokens):
		listing = []
		if tokens.is_complete():
			if not allow_nothing:
				raise UnexpectedLackOfToken(tokens)
		else:
			listing = [expect(tokens, subrule)]
		while not tokens.is_complete():
			if tokens.peek(0, *delimiters):
				tokens.eat_details()
			listing.append(expect(tokens, subrule))
		if len(listing) == 1 and not always_package:
			return listing[0]
		if binding == DelimitedBinding.DONT_PROCESS or binding == DelimitedBinding.DROP_AND_FLATTEN:
			return {
				'#': type,
				'items': listing
			}
		elif binding == DelimitedBinding.LEFT_FIRST:
			listing = list(listing[::-1])
			value = listing.pop()
			while listing:
				value = {
					'#': type,
					'left': value,
					'right': listing.pop()
				}
			return listing
		elif binding == DelimitedBinding.RIGHT_FIRST:
			value = listing.pop()
			while listing:
				value = {
					'#': type,
					'left': listing.pop(),
					'right': value
				}
			return listing

	internal.__name__ == 'eat_optionally_delimited__' + type
	return internal


def atom(tokens):
	if tokens.peek(0, 'number', 'word', 'string', 'glyph'):
		return tokens.eat_details()
	raise UnableToFinishParsing(tokens)


def percentage(tokens):
	if tokens.peek_sequence(0, 'number', 'percent_op'):
		return {
			'#': 'percent_op',
			'value': atom(tokens),
			'token': tokens.eat_details()
		}
	return atom(tokens)


def word(tokens):
	if tokens.peek(0, 'word'):
		return tokens.eat_details()
	raise UnableToFinishParsing(tokens)


def list_literal(tokens):
	r = _argument_list(tokens)
	r['#'] = 'list_literal'
	return r


def wrapped_expression(tokens):
	if tokens.peek(0, BracketType.ROUND):
		return ensure_completed(expression, tokens.eat_details())
	if tokens.peek(0, BracketType.SQUARE):
		return ensure_completed(list_literal, tokens.eat_details())
	return percentage(tokens)


def function_call(tokens):
	# Slightly 'intelligent' parsing, since integers
	# cannot be called as functions
	if tokens.peek(0, 'number'):
		return percentage(tokens)
	value = wrapped_expression(tokens)
	calls = []
	while tokens.peek(0, BracketType.ROUND) and not tokens.peek(1, 'function_definition'):
		calls.append(ensure_completed(argument_list, tokens.eat_details()))
	calls = calls[::-1]
	while calls:
		value = {
			'#': 'function_call',
			'function': value,
			'arguments': calls.pop()
		}
	return value


def operator_list_extract(tokens):
	if tokens.peek(0, 'head_op'):
		return {
			'#': 'head',
			'token': tokens.eat_details(),
			'expression': expect(tokens, operator_list_extract)
		}
	if tokens.peek(0, 'tail_op'):
		return {
			'#': 'tail',
			'token': tokens.eat_details(),
			'expression': expect(tokens, operator_list_extract)
		}
	return function_call(tokens)


def logic_not(tokens):
	if tokens.peek(0, 'bang'):
		token = tokens.eat_details()
		return {
			'#': 'not',
			'token': token,
			'expression': expect(tokens, logic_not)
		}
	return operator_list_extract(tokens)


def factorial(tokens):
	value = logic_not(tokens)
	while tokens.peek(0, 'bang'):
		token = tokens.eat_details()
		value = {
			'#': 'factorial',
			'token': token,
			'value': value
		}
	return value


SUPERSCRIPT_MAP = {
	ord('⁰'): '0',
	ord('¹'): '1',
	ord('²'): '2',
	ord('³'): '3',
	ord('⁴'): '4',
	ord('⁵'): '5',
	ord('⁶'): '6',
	ord('⁷'): '7',
	ord('⁸'): '8',
	ord('⁹'): '9'
}

def superscript(tokens):
	result = factorial(tokens)
	while tokens.peek(0, 'superscript'):
		tok = tokens.eat_details()
		result = {
			'#': 'bin_op',
			'operator': '^',
			'token': tok,
			'left': result,
			'right': {
				'#': 'number',
				'string': tok['string'].translate(SUPERSCRIPT_MAP),
				'position': tok['position']
			}
		}
	return result


def expression(tokens):
	return function_definition(tokens, 'function_definition')


_parameter_list = eat_optionally_delimited(
	word,
	['comma'],
	DelimitedBinding.DROP_AND_FLATTEN,
	'parameters',
	allow_nothing=True,
	always_package=True
)


def parameter_list(tokens):
	# params = _parameter_list(tokens)
	params = []
	while tokens.peek(0, 'word', 'comma'):
		while tokens.peek_and_eat(0, 'comma'):
			pass
		params.append(expect(tokens, word))
	is_variadic = False
	if tokens.peek_and_eat(0, 'period'):
		is_variadic = True
	return {'#': 'parameters', 'items': params}, is_variadic


_argument_list = eat_optionally_delimited(expression,
	['comma'],
	DelimitedBinding.DROP_AND_FLATTEN,
	'parameters',
	allow_nothing=True,
	always_package=True
)


def argument_list(tokens):
	result = _argument_list(tokens)
	if result is not None:
		result['edges'] = {
			'start': tokens.edge_start,
			'end': tokens.edge_end
		}
	return result


def power(tokens):
	left = superscript(tokens)
	if tokens.peek(0, 'pow_op'):
		t = tokens.eat_details()
		return {
			'#': 'bin_op',
			'operator': '^',
			'token': t,
			'left': left,
			'right': expect(tokens, uminus)
		}
	return left


def uminus(tokens):
	if tokens.peek_string(0, '-'):
		t = tokens.eat_details()
		return {
			'#': 'uminus',
			'token': t,
			'value': expect(tokens, uminus)
		}
	return power(tokens)


# power     = eat_delimited(uminus,    ['pow_op'],  BINDING_RIGHT, 'bin_op')
modulo    = eat_delimited(uminus,    ['mod_op'],  DelimitedBinding.LEFT_FIRST,  'bin_op')
product   = eat_delimited(modulo,    ['mul_op'],  DelimitedBinding.LEFT_FIRST,  'bin_op')
addition  = eat_delimited(product,   ['add_op'],  DelimitedBinding.LEFT_FIRST,  'bin_op')

def comparison_list(tokens):
	result = addition(tokens)
	if result and tokens.peek(0, 'comp_op'):
		result = {
			'#': 'comparison',
			'first': result,
			'rest': [],
		}
		while tokens.peek(0, 'comp_op'):
			token = tokens.eat_details()
			value = addition(tokens)
			result['rest'].append({
				'operator': token['string'],
				'token': token,
				'value': value
			})
	return result


logic_and = eat_delimited(comparison_list,  ['land_op'], DelimitedBinding.LEFT_FIRST,  'bin_op')
logic_or  = eat_delimited(logic_and, ['lor_op'],  DelimitedBinding.LEFT_FIRST,  'bin_op')
prepend_op = eat_delimited(logic_or, ['prepend_op'], DelimitedBinding.RIGHT_FIRST, 'bin_op')


def function_definition(tokens, delimiter):
	if tokens.peek(1, delimiter):
		if tokens.peek(0, BracketType.ROUND):
			args, is_variadic = ensure_completed(parameter_list, tokens.eat_details())
		elif tokens.peek(0, 'word'):
			args = {
				'#': 'parameters',
				'items': [tokens.eat_details()]
			}
			is_variadic = False
		else:
			raise UnableToFinishParsing(tokens)
		kind = tokens.eat_details()
		expr = expression(tokens)
		return {
			'#': 'function_definition',
			'parameters': args,
			'kind': kind['string'],
			'expression': expr,
			'variadic': is_variadic,
			'token': kind
		}
	return prepend_op(tokens)


def statement(tokens):
	if tokens.peek_sequence(0, 'word', 'assignment'):
		name = word(tokens)
		tokens.eat_details()
		value = expression(tokens)
		return {
			'#': 'assignment',
			'variable': name,
			'value': value
		}
	elif tokens.peek(0, 'kw_symbol'):
		tokens.eat_details()
		name = word(tokens)
		return {
			'#': 'declare_symbol',
			'name': name
		}
	elif tokens.peek(0, 'kw_unload'):
		tokens.eat_details()
		name = word(tokens)
		return {
			'#': 'unload_global',
			'variable': name
		}
	elif tokens.peek_sequence(0, 'word', BracketType.ROUND, 'function_definition'):
		tokens.eat_details()
		tokens.eat_details()
		raise DeprecatedSyntax(tokens)
	elif tokens.peek_sequence(0, 'word', BracketType.ROUND, 'assignment'):
		name = word(tokens)
		function = function_definition(tokens, 'assignment')
		function['name'] = name['string']
		return {
			'#': 'assignment',
			'variable': name,
			'value': function
		}
	return expression(tokens)


program = eat_optionally_delimited(statement, ['comma'], DelimitedBinding.DROP_AND_FLATTEN, 'program')


def process_tokens(tokens):
	tokens = tokens[::]
	# Check that the brackets are balanced
	stack = []
	for tok in tokens:
		btype = bracket_type(tok['string'])
		if btype != BracketType.NONE:
			bdir = bracket_direction(tok['string'])
			if bdir == BracketDirection.LEFT:
				stack.append(btype)
			elif not stack or stack.pop() != btype:
				raise ImbalancedBraces(tok)
	if stack:
		raise ImbalancedBraces(tokens[-1])
	# Do the thing
	p_start = tokens.pop(0)
	p_end   = tokens.pop()
	tokens = tokens[::-1]
	def recurse(first_token):
		result = [first_token]
		while tokens:
			tok = tokens.pop()
			if tok['string'] in ['(', '[']:
				result.append(recurse(tok))
			elif tok['string'] in [')', ']']:
				result.append(tok)
				break
			else:
				result.append(tok)
		return result
	return recurse(p_start) + [p_end]


def run(string):
	tokens = parse(string)[1]
	try:
		result = ensure_completed(program, tokens.tokens)
	except ParseFailed as e:
		print('Parsing failed:')
		print(string)
		print(' ' * e.position + '^')
	else:
		print(result)
		print(json.dumps(result, indent = 4))


def run_script(module):
	filename = 'calculator/scripts/{}.c5'.format(module)
	with open(filename) as f:
		data = f.read()
	data = data.replace('\n', ' ')
	return run(data)


def tokenizer(original_string, ttypes, source_name = '__unknown__'):
	# print(string)
	regexes = [x if len(x) == 3 else (x[0], x[1], None) for x in ttypes]
	regexes = list(map(lambda x: (x[0], re.compile(x[1]), x[2]), regexes))
	result = [{
		'#': 'pseudotoken-start',
		'string': '',
		'position': 0,
	}]
	# Hard coded thing here, maybe remove it.
	string = original_string.replace('\t', ' ')
	location = 0
	while len(string) > 0:
		if string[0] in ' \n':
			string = string[1:]
			location += 1
		else:
			possible = []
			for name, cre, replacement in regexes:
				# print(i)
				match = cre.match(string)
				if match is not None:
					possible.append((name, replacement or match.group()))
			possible.sort(key = lambda x: len(x[1]), reverse = True)
			# print(possible)
			if len(possible) == 0:
				raise TokenizationFailed(location)
				# raise TokenizationFailed(original_string, len(original_string) - len(string))
			# print(possible[0][1])
			if possible[0][0] == '__illegal__':
				raise TokenizationFailed(location)
			if possible[0][0] != '__remove__':
				result.append({
					'#': possible[0][0],
					'string': possible[0][1],
					'position': location,
					'source': {
						'name': source_name,
						'code': original_string,
						'position': location
					}
				})
			location += len(possible[0][1])
			string = string[len(possible[0][1]):]
	result.append({
		'#': 'pseudotoken-end',
		'string': '',
		'position': len(original_string.rstrip()) + 1
	})
	for i, v in enumerate(result):
		v['index'] = i
	return result

TOKEN_SPEC = [
	('__remove__', r'#.*'),
	('kw_symbol', r'symbol\?'),
	('kw_unload', r'unload\?'),
	('__illegal__', r'\d*\.?\d+[eE][+-]?\d{6,}i?'),
	('number', r'\d*\.?\d+([eE][+-]?\d+)?i?'),
	('string', r'"(?:\\.|[^\\"])*"'),
	('string', r'“(?:\\.|[^\\”])*”'),
	('glyph', r';\\.|;[^\\]'),
	('word', r'π|τ|∞|[a-zA-Z_][a-zA-Z0-9_]*'),
	# ('die_op', r'd'),
	('pow_op', r'\^'),
	('superscript', r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+'),
	('percent_op', r'\%'),
	('mod_op', r'~mod'),
	('mul_op', r'[/÷]', '/'),
	('mul_op', r'[*×]', '*'),
	('add_op', r'[+-]'),
	('comp_op', r'<=|>=|≤|≥|<|>|≮|≯|!=|==|≠'),
	('paren', r'\(|\)'),
	('bracket', r'\[|\]'),
	('function_definition', r'~>|->'),
	('comma', r','),
	('assignment', r'='),
	('land_op', r'&&'),
	('lor_op', r'\|\|'),
	('bang', r'!'),
	('period', r'\.'),
	('head_op', r'\''),
	('tail_op', r'\\'),
	('prepend_op', r':'),
	('concat_op', r'\+\+'),
	('__illegal__', r'\d*\.?\d+([eE]-?\d+)?i?[a-zA-Z_][a-zA-Z0-9_]*')
]


def parse(string, source_name = '__unknown__'):
	string = string.replace('\N{SINGLE LOW-9 QUOTATION MARK}', '')
	tokens = tokenizer(string, TOKEN_SPEC, source_name = source_name)
	nested = process_tokens(tokens)
	package = TokenRoot(string, tokens, nested)
	result = ensure_completed(program, package.tokens)
	return package, result
