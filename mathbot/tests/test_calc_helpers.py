import calculator
import pytest
import math
import cmath
import sympy

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

def compile_fail(equation):
	with pytest.raises(calculator.errors.CompilationError):
		calculator.calculate(equation, tick_limit = TIMEOUT)

def parse_fail(equation):
	with pytest.raises(calculator.parser.ParseFailed):
		calculator.calculate(equation, tick_limit = TIMEOUT)