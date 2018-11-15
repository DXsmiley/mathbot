'''
    The works of a madman, trying to turn Python
    into something it's not.

    Sequences of different things:

        rule1 & rule2 & rule3

    Multiple of one thing:

        many(rule)

    Alternative options:

        reul1 | rule2 | rule3

    Processing results:

        rule >> processor

    Lookahead checks

        If rule1 parses, parse using rule 2, failing
        if rule2 fails.

            rule1 / rule2

        If rule 1 parse, parse using rule 2

            rule1 / rule2

    Mutual recursion

        Declare your rules first, then define them:

        rule1 = predef()
        rule2 = predef()
        rule1 *= (Token('a') + rule2) | Token('c')
        rule2 *= Token('b') + rule1

'''

import abc
import functools

from calculator.tokenizer import Token as TToken


def bailwrapper(function):
    @functools.wraps(function)
    def internal(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except FailUpwards as e:
            return e.to_result()
        except BadResult as e:
            return e
    return internal


def singleton(cls):
    return cls()


class ListView:

    def __init__(self, lst, left=None, right=None):
        self.lst   = lst
        self.left  =        0 if left  is None else left
        self.right = len(lst) if right is None else right

    def __len__(self):
        return self.right - self.left

    def _procindex(self, index, default=None):
        if index is None:
            return default
        if index >= 0:
            if index >= len(self):
                raise IndexError
            return self.left + index
        if index < -len(self):
            raise IndexError
        return self.right + index

    def __getitem__(self, key):
        if isinstance(key, slice):
            assert key.step in [1, None]
            return ListView(
                self.lst,
                self._procindex(key.start, self.left),
                self._procindex(key.stop, self.right)
            )
        return self.lst[self._procindex(key)]

    def __iter__(self):
        for i in range(self.left, self.right):
            yield self.lst[i]


class Combinator(abc.ABC):

    def __or__(self, other):
        return Or(self, other)

    def __and__(self, other):
        return And([self, other])

    def __truediv__(self, nextparser):
        return LookAheadCheck(self, nextparser)

    def __div__(self, nextparser):
        return LookAheadCheck(self, Commit(nextparser))

    def __rshift__(self, processor):
        # return self
        return SuccessProcessor(self, processor)

    @abc.abstractmethod
    def parse(self, tokens):
        ''' The parse function should take a list of tokens,
            and Result, return a new list of tokens, along with a
            'result' (usually some sort of syntax tree).
        ''' 
        pass

    def run(self, tokens):
        try:
            return self.parse(tokens)
        except CertainError as e:
            return e.result

    def parse_or_bail_success(self, value, tokens):
        result = self.parse(tokens)
        if result:
            return result
        raise FailUpwards(value, tokens)


class Trace(Combinator):

    def __init__(self, parser, label=None):
        self._parser = parser
        self._label = label

    def parse(self, tokens):
        try:
            result = self._parser.parse(tokens)
            if self._label:
                print(self._label, ':', tokens, '>', result)
            else:
                print(tokens, '>', result)
            return result
        except CertainError as e:
            if self._label:
                print(self._label, ':', tokens, '>', e.result)
            else:
                print(tokens, '>', e.result)
            raise e


class Optional(Combinator):

    def __init__(self, parser):
        self._parser = parser

    @bailwrapper
    def parse(self, tokens):
        return self._parser.parse_or_bail_success(None, tokens)


class Predef(Combinator):

    def __init__(self):
        self.combinator = None

    def __imul__(self, combinator):
        assert self.combinator is None
        self.combinator = combinator
        return self

    def parse(self, tokens):
        return self.combinator.parse(tokens)


@singleton
class EndOfLine(Combinator):

    def parse(self, tokens):
        if len(tokens) == 0:
            return GoodResult(None, tokens)
        return BadResult('Failed to get to the end of the tokens', tokens)


class Or(Combinator):

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
        for i in items:
            assert isinstance(i, Combinator)
        self.items = items

    @bailwrapper
    def parse(self, tokens):
        values = []
        for i in self.items:
            x = i.parse(tokens)
            result, tokens = x.failbail()
            values.append(result)
        return GoodResult(values, tokens)

    def __and__(self, other):
        return And(self.items + [other])


class Many(Combinator):

    def __init__(self, parser):
        self._parser = parser

    @bailwrapper
    def parse(self, tokens):
        result = []
        while True:
            peice, tokens = self._parser.parse_or_bail_success(result, tokens)
            result.append(peice)


class LookAheadCheck(Combinator):

    def __init__(self, check, parser):
        self._check = check
        self._parser = parser

    def parse(self, tokens):
        checkresult = self._check.parse(tokens)
        if checkresult:
            return self._parser.parse(tokens)
        return BadResult(checkresult.value, checkresult.tokens)


class Token(Combinator):

    def __init__(self, group):
        self.group = group

    def parse(self, tokens):
        if isinstance(tokens.head, TToken) and tokens.head.group == self.group:
            return GoodResult(tokens.head, tokens.rest)
        return BadResult(f'Expected {self.group}, found {tokens.head} instead', tokens)


class TokenMatchString(Combinator):

    def __init__(self, string):
        self.string = string

    def parse(self, tokens):
        if isinstance(tokens.head, TToken) and tokens.head.string == self.string:
            return GoodResult(tokens.head, tokens.rest)
        return BadResult(f'Expected "{self.string}", found "{tokens.head}" instead', tokens)


@singleton
class SkipToken(Combinator):

    def parse(self, tokens):
        if len(tokens) == 0:
            return BadResult('No token to skip', tokens)
        return GoodResult(None, tokens.rest)


class SuccessProcessor(Combinator):

    class YetToProcess:
        def __init__(self, value, function):
            self.value = value
            self.function = function

        def __repr__(self):
            return f'`{self.value}'

        def process(self):
            return self.function(postprocess(self.value))

    def __init__(self, parser, processor):
        self._parser = parser
        self._proc = processor

    def parse(self, tokens):
        return self._parser.parse(tokens).map(lambda v: SuccessProcessor.YetToProcess(v, self._proc))


class Commit(Combinator):

    def __init__(self, parser):
        self._parser = parser

    def parse(self, tokens):
        result = self._parser.parse(tokens)
        if result:
            return result
        raise CertainError(result)


class EnsureComplete(Combinator):

    def __init__(self, parser, message='Coult not finish parsing'):
        self._parser = parser
        self._message = message

    def parse(self, tokens):
        result = self._parser.parse(tokens)
        if not result:
            return result
        if not result.tokens.empty:
            return BadResult(self._message, result.tokens)
        return result


class Fail(Combinator):

    def __init__(self, message):
        self.message = message

    def parse(self, tokens):
        return BadResult(self.message, tokens)


class FailUpwards(Exception):

    def __init__(self, value, tokens):
        self.value = value
        self.tokens = tokens

    def to_result(self):
        return GoodResult(self.value, self.tokens)


class Delimited(Combinator):

    def __init__(self, contents, separator, *, drop_separators=False, pull_single=True):
        self.contents = contents
        self.separator = separator
        self.drop_separators = drop_separators
        self.pull_single = pull_single

    def __rshift__(self, processor):
        return ForcePullFromList(self, processor) if self.pull_single else SuccessProcessor(self, processor)

    @bailwrapper
    def parse(self, tokens):
        # Get the first element
        first, tokens = self.contents.parse(tokens).failbail()
        listing = [first]
        while True:
            # If there a seperator, grab it, otherwise return with what we have so far
            separator, tokens = self.separator.parse_or_bail_success(listing, tokens)
            if not self.drop_separators:
                listing.append(separator)
            # Parse the next element, if this fails, we have problems
            element, tokens = self.contents.parse(tokens).failbail()
            listing.append(element)


class ForcePullFromList(Combinator):

    # Not sure if I want this in the core lib...

    def __init__(self, parser, processor):
        self._parser = parser
        self._proc = processor

    def parse(self, tokens):
        return self._parser.parse(tokens).map(lambda v: v[0] if len(v) == 1 else SuccessProcessor.YetToProcess(v, self._proc))


class OptionallyDelimited(Combinator):

    def __init__(self, contents, separator, drop_separators=True):
        self.contents = Commit(contents)
        self.separator = separator
        self.drop_separators = drop_separators

    @bailwrapper
    def parse(self, tokens):
        # Get the first element, can be absent
        if tokens.empty:
            return GoodResult([], tokens)
        first, tokens = self.contents.parse(tokens).failbail()
        listing = [first]
        while True:
            # If there a seperator, grab it, otherwise return with what we have so far
            separator = self.separator.parse(tokens)
            if separator:
                sep_element, tokens = separator
                if not self.drop_separators:
                    listing.append(sep_element)
            # Parse the next element, if this fails, we have problems
            if tokens.empty:
                return GoodResult(listing, tokens)
            element, tokens = self.contents.parse(tokens).failbail()
            listing.append(element)


class Result(abc.ABC):

    def __str__(self):
        return f'{self.__class__.__name__}({repr(self.value)}, {self.tokens})'


class GoodResult(Result):

    def __init__(self, value, tokens):
        self.value = value
        self.tokens = tokens

    def __bool__(self):
        return True

    def map(self, function):
        return GoodResult(function(self.value), self.tokens)

    def __iter__(self):
        yield self.value
        yield self.tokens

    def failbail(self):
        return self


class BadResult(Result, Exception):

    def __init__(self, value, tokens):
        self.value = value
        self.tokens = tokens

    def __bool__(self):
        return False

    def map(self, function):
        return self

    def __iter__(self):
        yield self.value
        yield self.tokens

    def failbail(self):
        raise self


class CertainError(Exception):

    def __init__(self, result):
        self.result = result


def left_associative(func):
    ''' Assumes that func takes elements as LEFT OP RIGHT '''
    def transformer(lst):
        assert len(lst) % 2 == 1
        if len(lst) == 1:
            return lst[0]
        # TODO: create a "view into a list" to that this isn't quadratic
        return func(transformer(lst[:-2]), lst[-2], lst[-1])
    return transformer


def right_associative(func):
    ''' Assumes that func takes elements as LEFT OP RIGHT '''
    def transformer(lst):
        assert len(lst) % 2 == 1
        if len(lst) == 1:
            return lst[0]
        return func(lst[0], lst[1], transformer(lst[2:]))
    return transformer


def second(t):
    ''' Doing it like this, rather than using [ ] allows for generators to be passed in, or any other iterable'''
    a, b = t
    return b


def first(t):
    a, b = t
    return a


def flip(t):
    a, b = t
    return b, a


def flipargs(f):
    return lambda a, b: f(b, a)


def pick(*indexes):
    return lambda lst: [v for i, v in enumerate(lst) if i in indexes]


def lift_single(function):
    return lambda x: x[0] if len(x) == 1 else function(x)


def postprocess(result):
    if isinstance(result, list):
        return [postprocess(i) for i in result]
    if isinstance(result, tuple):
        return tuple([postprocess(i) for i in result])
    if isinstance(result, SuccessProcessor.YetToProcess):
        return result.process()
    if result is None or isinstance(result, (str, TToken)):
        return result
    return result
    raise TypeError(f'Did not expect a {type(result)} object in postprocess')


# def on_multiple(internal):
#   def transformer(lst):
#       return internal(lst) if len(lst) > 1 else lst
#   return transformer
