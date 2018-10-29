from combinator import *
from syntax_trees import *
from tokenizer import tokenize
import tokenizer
import functools
import itertools
from util import foldr


class _PrecheckParenthesised(Combinator):

	def __init__(self, kind):
		self._kind = kind

	def parse(self, tokens):
		if isinstance(tokens.head, tokenizer.Bracketed) and tokens.head.start.string == self._kind:
			return GoodResult(True, tokens.rest)
		return BadResult(False, tokens.rest)

PrecheckParenthesised = _PrecheckParenthesised('(')
PrecheckBracketed = _PrecheckParenthesised('[')


class _Parenthesised(Combinator):

	def __init__(self, parser, kind):
		self._parser = EnsureComplete(parser)
		self._kind = kind

	@bailwrapper
	def parse(self, tokens):
		if not isinstance(tokens.head, tokenizer.Bracketed) or tokens.head.start.string != self._kind:
			return BadResult('Expected parenthesised block', tokens)
		value, _ = self._parser.parse(tokens.head.contents).failbail()
		return GoodResult(value, tokens.rest)

Parenthesised = lambda x: _Parenthesised(x, '(')
Bracketed = lambda x: _Parenthesised(x, '[')


class Not(Combinator):

	''' This is pretty dodgy, NGL '''

	def __init__(self, parser):
		self._parser = parser

	def parse(self, tokens):
		result = self._parser.parse(tokens)
		if result:
			return BadResult('Found something unexpected', tokens)
		return GoodResult(None, tokens)


def unimplemented(x):
	return x


unable_to_finish_parsing = BadResult
number = Token('number') >> Number
word = Token('word') >> Word
string = Token('string')
glyph = Token('glyph')
percent_op = Token('%')

expression = Predef()
expression_list = OptionallyDelimited(expression, Token('comma'))
list_literal = (PrecheckBracketed / Bracketed(expression_list)) >> ListLiteral


def spread(f):
	return lambda a: f(*a)

atom = number | word | string | glyph | Fail('expected an atom')

percentage = (number & percent_op) >> Percentage

bracketed_expression = PrecheckParenthesised / Parenthesised(expression)
wrapped_expression = bracketed_expression \
                   | list_literal \
                   | percentage \
                   | atom

function_arguments = (PrecheckParenthesised & Not(Token('function_definition'))) \
				   /  Parenthesised(expression_list)

_reduce_function_call = lambda x: functools.reduce(FunctionCall, x[1], x[0])
function_call = percentage \
              | number \
              | ((wrapped_expression & Many(function_arguments)) >> _reduce_function_call)

operator_list_extract  = Predef()
operator_list_extract *= ((Token('head_op') & operator_list_extract) >> spread(HeadOperator)) \
                       | ((Token('tail_op') & operator_list_extract) >> spread(TailOperator)) \
                       | function_call

logical_not  = Predef()
logical_not *= ((Token('bang') & logical_not) >> spread(LogicalNotOperator)) \
             | operator_list_extract

# Will not pretty print correctly.
factorial = (logical_not & Many(Token('bang'))) >> (lambda x: functools.reduce(flipargs(FactorialOperator), x[1], x[0]))

# superscript goes in here, but do we really want it to be a thing anymore??
superscript = factorial

# I'm dropping support for variadic functions
# Needs something about brackets here
parameter_list = Parenthesised(OptionallyDelimited(word | Fail('Parameter list should be a sequence of words'), Token('comma'))) >> ParameterList

# argument_list = (OptionallyDelimited(expression, Token('comma')) & EndOfLine) >> first >> ArgumentList

uminus  = Predef()
_power  = lambda x: x[0] if x[1] is None else BinaryOperator(x[0], x[1][0], x[1][1])
power   = (superscript & Optional(Token('pow_op') & uminus)) >> _power
uminus *= ((Token('-') & uminus) >> spread(MinusOperator)) | power

_delim = lambda c, s: Delimited(c, s, pull_single=True)
modulus     = _delim(uminus,   Token('mod_op'))  >> left_associative(ModulusOperator)
product     = _delim(modulus,  Token('mul_op'))  >> left_associative(ProductOperator)
addition    = _delim(product,  Token('add_op'))  >> left_associative(AdditionOperator)
comparisons = _delim(addition, Token('comp_op')) >> ComparisonChain

logical_and = _delim(comparisons, Token('land_op'))    >> left_associative(LogicalAndOperator)
logical_or  = _delim(logical_and, Token('lor_op'))     >> left_associative(LogicalOrOperator)
prepend_op  = _delim(logical_or,  Token('prepend_op')) >> right_associative(PrependOperator)

def _funcdef(marker):
    params = (word >> (lambda x: ParameterList([x]))) | parameter_list
    parser = (params & Token(marker) & Commit(expression)) >> pick(0, 2) >> spread(FunctionDefinition)
    return ((word | PrecheckParenthesised) & Token(marker)) / parser

assignment = (word & Token('assignment') & Commit(expression)) \
             >> pick(0, 2) >> spread(Assignment)
sleek_function_definition = ((word & PrecheckParenthesised & Token('assignment')) \
                          /  (word & _funcdef('assignment'))) >> spread(Assignment)
statement = assignment | sleek_function_definition | expression

def _program(listing):
	is_assignment = lambda x: isinstance(x, Assignment)
	return Program(
		[i for i in listing if is_assignment(i)],
		[i for i in listing if not is_assignment(i)],
	)
program = EnsureComplete(OptionallyDelimited(Commit(statement), Token('comma'))) >> _program

expression *= _funcdef('function_definition') | prepend_op


def process(string):
	try:
		t = tokenize(string)
	except tokenizer.TokenizationFailed as e:
		print_source_marker_at_location(string, e.location)
		assert False
	else:
		print(f'===== {string} =====')
		print(t)
		result = program.run(t)
		print(result)
		if result:
			processed = result.map(postprocess)
			print(processed.value)
		else:
			print(result.value)
			print_source_marker_at_token(result.tokens.first_token)
		return str(result.map(postprocess).value)


def multistep(string):
	a = process(string)
	b = process(a)
	c = process(b)
	assert a == b == c


def print_source_marker_at_token(token):
	print_source_marker_at_location(token.source, token.location)


def print_source_marker_at_location(source, location):
	lines = source.split('\n')
	cur = source.count('\n', 0, location)
	print(location)
	print('\n'.join(lines[cur-5:cur+1]))
	print(' ' * (location - cur - sum(map(len, lines[:cur]))) + '^')
	print('\n'.join(lines[cur+1:cur+5]))


if __name__ == '__main__':
	process('''
x = 1 + 2
x = 1 * 2 + 3
y = 1 < 2 >= 3
f(x) = x + y
f(x, y) = x + y
f(x) = (x + 1)
f(x) = y -> x + y
	''')
	process('f(x)')
	process('f(x + 2, y)')
	process('f(x + 2 y)')
	process('f(x)(y)')
	process('x + ((y + x) + q)')
	process('(x -> x)(3)')
	multistep(open('calculator/library.c5').read().replace('\t', '    '))
