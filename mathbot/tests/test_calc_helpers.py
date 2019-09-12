import calculator
import pytest
import math
import cmath
import sympy
import collections

from random import randint

TIMEOUT = 30000

class Ignore: pass

def check_string(list, expected):
	if not isinstance(expected, str):
		return False
	assert isinstance(list, calculator.functions.ListBase)
	assert len(list) == len(expected)
	for g, c in zip(list, expected):
		assert g.value == c
	return True

def doit(equation, expected, use_runtime=False):
	result = calculator.calculate(equation, tick_limit = TIMEOUT, use_runtime=use_runtime, trace=False)
	assert expected is Ignore \
		or isinstance(result, calculator.functions.Glyph) and result.value == expected \
		or check_string(result, expected) \
		or result is None and expected is None \
		or isinstance(result, sympy.boolalg.BooleanAtom) and bool(result) == expected \
		or sympy.simplify(result - expected) == 0

def asrt(equation):
	dort(equation, True)

def dort(equation, expected):
	doit(equation, expected, use_runtime=True)

def doformatted(equation, expected):
	result = calculator.calculate(equation, tick_limit = TIMEOUT)
	formatted = calculator.formatter.format(result)
	assert formatted == expected

def repeat(equation, start, end):
	for i in range(20):
		r = calculator.calculate(equation, tick_limit = TIMEOUT)
		assert start <= r <= end

def throws(equation):
	with pytest.raises(calculator.errors.EvaluationError):
		calculator.calculate(equation, tick_limit = TIMEOUT, use_runtime=True)

def tokenization_fail(equation):
	with pytest.raises(calculator.parser.TokenizationFailed):
		calculator.calculate(equation, tick_limit = TIMEOUT)

def compile_fail(equation):
	with pytest.raises(calculator.errors.CompilationError):
		calculator.calculate(equation, tick_limit = TIMEOUT)

def parse_fail(equation):
	with pytest.raises(calculator.parser.ParseFailed):
		calculator.calculate(equation, tick_limit = TIMEOUT)

def gen_random_deep_list(i=5):
    l = [0]

    for _ in range(i):
        l.append(gen_random_deep_list(randint(0,i - 1)))
    
    return l

def flatten(x):
    '''
    Flattens an irregularly nested list of lists.
    https://stackoverflow.com/a/2158522
    '''
    if isinstance(x, collections.Iterable):
        return [a for i in x for a in flatten(i)]
    else:
        return [x]


def joinit(iterable, delimiter):
    '''
    Interleave an element into an iterable.
    https://stackoverflow.com/a/5656097
    '''
    it = iter(iterable)
    yield next(it)
    for x in it:
        yield delimiter
        yield x