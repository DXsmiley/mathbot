import re


class TokenElement:
	pass


class Token(TokenElement):

	def __init__(self, group, string, source, location):
		self.group = group
		self.string = string
		self.source = source
		self.location = location

	def __str__(self):
		return self.string

	def __repr__(self):
		return f'{self.group}:{self.string}'

	@property
	def first_token(self):
		return self


class Bracketed(TokenElement):

	def __init__(self, start, contents, end):
		self.start = start
		self.contents = contents
		self.end = end

	def __str__(self):
		return f'{self.start} {self.contents} {self.end}'

	def __repr__(self):
		return f'b({self.start}{self.end} | {self.contents})'

	@property
	def first_token(self):
		return self.start.first_token

	@property
	def group(self):
		return self.start.group

	# @property
	# def string(self):
	# 	return self.start.string


class Tokens:

    def __init__(self, tokens):
        self.tokens = tokens

    def __len__(self):
        return len(self.tokens)

    @property
    def head(self):
        return self.tokens[0] if self.tokens else None

    @property
    def rest(self):
        return Tokens(self.tokens[1:])

    @property
    def empty(self):
        return len(self.tokens) == 0

    @property
    def first_token(self):
    	return self.tokens[0].first_token

    def __repr__(self):
        return f'T[{", ".join(map(repr, self.tokens))}]'


BRACKET_PAIRS = [
	('(', ')'),
	('[', ']'),
	('{', '}')
]

BRACKETS_LEFT = [a for a, b in BRACKET_PAIRS]
BRACKETS_RIGHT = [b for a, b in BRACKET_PAIRS]
BRACKET_TO_MATCHING = dict(BRACKET_PAIRS + [(b, a) for a, b in BRACKET_PAIRS])


TOKEN_SPEC = [
	('__remove__', r'#.*'),
	('kw_symbol', r'symbol\?'),
	('kw_unload', r'unload\?'),
	('number', r'\d*\.?\d+([eE][+-]?\d+)?i?'),
	('string', r'"(?:\\.|[^\\"])*"'),
	('glyph', r';\\.|;[^\\]'),
	('word', r'π|τ|∞|[a-zA-Z_][a-zA-Z0-9_]*'),
	('pow_op', r'\^'),
	('superscript', r'[⁰¹²³⁴⁵⁶⁷⁸⁹]+'),
	('percent_op', r'\%'),
	('mod_op', r'~mod'),
	('mul_op', r'[/÷]', '/'),
	('mul_op', r'[*×]', '*'),
	('add_op', r'[+-]'),
	('comp_op', r'<=|>=|<|>|!=|=='),
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


def _compile_tokens():
	regexes = [x if len(x) == 3 else (x[0], x[1], None) for x in TOKEN_SPEC]
	regexes = list(map(lambda x: (x[0], re.compile(x[1]), x[2]), regexes))
	return regexes

TOKENS_REGEXES = _compile_tokens()


def _tokenize(original_string, source_name = '__unknown__'):
	# result = [{
	# 	'#': 'pseudotoken-start',
	# 	'string': '',
	# 	'position': 0,
	# }]
	result = []
	# Hard coded thing here, maybe remove it.
	string = original_string.replace('\t', ' ')
	location = 0
	while len(string) > 0:
		if string[0] in ' \n':
			string = string[1:]
			location += 1
		else:
			possible = []
			for name, cre, replacement in TOKENS_REGEXES:
				# print(i)
				match = cre.match(string)
				if match is not None:
					possible.append((name, replacement or match.group()))
			possible.sort(key = lambda x: len(x[1]), reverse = True)
			# print(possible)
			if len(possible) == 0:
				print(original_string)
				raise TokenizationFailed(location)
				# raise TokenizationFailed(original_string, len(original_string) - len(string))
			group, matched = possible[0]
			# print('>', group, matched)
			# print(possible[0][1])
			if group == '__illegal__':
				print(original_string)
				raise TokenizationFailed(location)
			if group != '__remove__':
				result.append(Token(group, matched, original_string, location))
			location += len(matched)
			string = string[len(matched):]
	# result.append({
	# 	'#': 'pseudotoken-end',
	# 	'string': '',
	# 	'position': len(original_string.rstrip()) + 1
	# })
	return result


def _group(tokens):
	stack = [[]]
	for t in tokens:
		if t.string in BRACKETS_LEFT:
			stack.append([t])
		elif t.string in BRACKETS_RIGHT:
			if stack[-1][0].string != BRACKET_TO_MATCHING[t.string] or len(stack) < 2:
				raise Exception('Bracketing is bad :(')
			s = stack.pop()
			stack[-1].append(
				Bracketed(
					s[0],
					Tokens(s[1:]),
					t
				)
			)
		else:
			stack[-1].append(t)
	if len(stack) != 1:
		raise Exception('Bracketing is bad :(')
	return Tokens(stack[0])

def tokenize(string):
	return _group(_tokenize(string))
