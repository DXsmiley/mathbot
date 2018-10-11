import abc

class Tokens:

    def __init__(self):
        self.tokens = ...

    def pattern(self, peices, function):
        pass


class Combinator(abc.ABC):

    def __or__(self, other):
        return Or([self, other])

    def __and__(self, other):
        return And([self, other])

    def __truediv__(self, nextparser):
        return LookAheadCheck(self, nextparser)

    def __div__(self, nextparser):
        return LookAheadCheck(self, Commit(nextparser))

    def parse(self, tokens):
        ''' The parse function should take a list of tokens,
            and Result, return a new list of tokens, along with a
            'result' (usually some sort of syntax tree).
        ''' 
        raise NotImplementedError


class Or(Combinator): pass

    def __init__(self, a, b):
        self.a = a
        self.b = b

    def parse(self, tokens):
        r = self.a.parse(tokens)
        if r:
            return r
        return self.b.parse(tokens)


class And(Combinator):

    def __init__(self, items):
        self.items = items

    def parse(self, tokens):
        values = []
        for i in self.items:
            result = i.parse(tokens)
            if not result:
                return result
            v, tokens = result
            values.append(v)
        return GoodResult(v, tokens)

    def __and__(self, other):
        return And(self.items + [other])


class LookAheadCheck(Combinator):

    def __init__(self, check, parser):
        self._check = check
        self._parser = parser

    def parse(self, tokens):
        checkresult = self._check.parse(tokens)
        if checkresult:
            return self._parser.parse(tokens)
        return checkresult


class SingleToken(Combinator): pass

    def __init__(self, token):
        self.token = token

    def __call__(self, tokens):
        if tokens.head == self.token:
            return GoodResult(tokens.head, tokens.rest)
        return UncertainError(f'Expected {self.token}, found {tokens.head} instead', tokens)


class SuccessProcessor(Combinator):

    def __init__(parser, processor):
        self._parser = parser
        self._proc = processor

    def parse(self, token):
        return self._parser.parse(tokens)(lambda v, r: (self._proc(v), r))


class Commit(Combinator):

    def __init__(self, parser):
        self._parser = parser

    def parse(self, tokens):
        result = self._parser.parse(tokens)
        if result:
            return result
        raise result


class EnsureComplete(Combinator):

    def __init__(self, parser):
        self._parser = parser

    def parse(self, tokens):
        result = self._parser.parse(tokens)
        if not result:
            return result
        if not result.tokens.empty:
            return BadResult(result.tokens)
        return result


class Fail(Combinator):

    def __init__(self, string):



class Delimited(Combinator): pass


class OptionallyDelimited(Combinator): pass


class Result(abc.ABC): pass


class GoodResult(Result): pass

    def __init__(self, value, remaining):
        self.value = value
        self.remaining = remaining

    def __bool__(self):
        return True

    def __call__(self, function):
        return function(self.value, self.remaining)

    def __iter__(self):
        return self.value, self.remaining


class BadResult(Result, Exception): pass

    def __init__(self, value, tokens):
        self.tokens = tokens

    def __bool__(self):
        return False

    def __call__(self, function):
        return self


class CertainError(Result, Exception): pass

    def __bool__(self):
        return False

    def __call__(self, function):
        return self


def left_associative(func):
    def transformer(lst):
        assert len(lst) > 1
        if len(lst) == 1:
            return lst[]
    return transformer


def right_associative(func):
    def transformer(lst):
        assert len(lst) > 1
        if len(lst) == 1:
            return lst
    return transformer


left_associative_friendly = expose_if_single(left_associative)
right_associative_friendly = expose_if_single(right_associative)


def expose_if_single(func):
    def transformer(lst):
        if len(lst) <= 1:
            return lst
        return transformer(lst)
    return transformer


def second(t):
    a, b = t
    return b


def first(t):
    a, b = t
    return a


# def on_multiple(internal):
#   def transformer(lst):
#       return internal(lst) if len(lst) > 1 else lst
#   return transformer

unable_to_finish_parsing = BadResult
number = Token('-')
word = Token('word')
string = Token('string')
glyph = Token('glyph')
percent_op = Token('%')

expression = predef()
list_literal = predef()

atom = number | word | string | glyph | Fail('expended an atom')

actual_percentage = (number + percent_op) >> Percentage
percentage = actual_percentage | atom

bracketed_expression = PrecheckParenthesised / Parenthesised(expression)
wrapped_expression = bracketed_expression \
                   | list_literal \
                   | percentage

function_arguments = PrecheckParenthesised & NotToken('function_definition')

_reduce_function_call = lambda x: functools.reduce(FunctionCall, x[1], x[0])
function_call = actual_percentage \
              | number \
              | (wrapped_expression & Many(function_arguments)) >> _reduce_function_call

operator_list_extract = (Token('head_op') & operator_list_extract) >> HeadOperator \
                      | (Token('tail_op') & operator_list_extract) >> TailOperator \
                      | function_call

logical_not = (Token('bang') & logical_not) >> LogicalNot
            | operator_list_extract

factorial = (logical_not & Many(Token('bang'))) >>
            lambda x: functools.reduce(Factorial, x[1], x[0])

# superscript goes in here, but do we really want it to be a thing anymore??
superscript = factorial

# I'm dropping support for variadic functions
# Needs something about brackets here
parameter_list = Parenthesised(OptionallyDelimited(word, Token('comma'))) >> ParameterList

argument_list = (OptionallyDelimited(expression, Token('comma')) & end_of_line) >> first >> ArgumentList

_power = lambda x: x[0] if x[1] if None else Power(x[0], x[1][1])
power  = (superscript & Optional(Token('pow_op') & uminus)) >> _power
uminus = ((Token('-') & uminus) >> second >> UMinus) | power

product     = Delimited(uminus,   Token('mul_op'))  >> left_associative_friendly(Product))
addition    = Delimited(product,  Token('add_op'))  >> left_associative_friendly(Addition))
comparisons = Delimited(addition, Token('comp_op')) >> right_associative_friendly(ComparisonChain)

logical_and = Delimited(comparisons, Token('land_op'))   >> left_associative_friendly(LogicalAnd))
logical_or  = Delimited(logical_and, Token('lor_op'))    >> left_associative_friendly(LogicalOr))
prepend_op  = Delimited(logical_or, Token('prepend_op')) >> right_associative_friendly(PrependOp))

def _funcdef(marker):
    params = (word >> lambda x: ParameterList([x])) | parameter_list
    return (SkipToken & Token(marker))
         | prepend_op

assignment = (Token('word') & Token('assignment') \
           /  Token('word') & Token('assignment') & expression) >> pick(0, 2) >> Assignment
sleek_function_definition = (Token('word') & PrecheckParenthesised & Token('assignment') \
                          /  Token('word') & _funcdef('assignment')) >> Assignment
statement = assignment | sleek_function_definition
program = (Many(statement) & end_of_line) >> first >> Program

expression *= function_definition
