from mathbot import calculator
import pytest
import math
import cmath
import sympy

from tests.test_calc_helpers import *

def test_negation():
	doit("9", 9)
	doit("-9", -9)
	# doit("--9", 9)
	doit("(9)", 9)
	doit("(-9)", -9)
	# doit("(--9)", 9)
	dort("-E", -sympy.E)
	doit('3-2', 1)
	doit('3 - 2', 1)
	doit('-2^2', -4)
	doit('(-2)^2', 4)
	doit('2^-1', 1/2)

def test_4func():
	doit("9 + 3 + 6", 9 + 3 + 6)
	doit("9 + 3 / 11", 9 + 3.0 / 11)
	doit("(9 + 3)", (9 + 3))
	doit("(9+3) / 11", (9+3.0) / 11)
	doit("9 - 12 - 6", 9 - 12 - 6)
	doit("9 - (12 - 6)", 9 - (12 - 6))
	doit("3 * -5", 3 * -5)
	doit("3 * (-5)", 3 * (-5))
	doit("2*3.14159", 2*3.14159)
	doit("3.1415926535*3.1415926535 / 10", 3.1415926535*3.1415926535 / 10)
	doit("6.02E23 * 8.048", 6.02E23 * 8.048)
	# doit("6.02E23 x 8.048", 6.02E23 * 8.048)

def test_modulo():
	doit('5 ~mod 2', 1)
	doit('10 ~mod 4', 2)
	throws('10 ~mod 0')

def test_constants():
	dort("PI * PI / 10", sympy.pi * sympy.pi / 10)
	dort("PI*PI/10", sympy.pi*sympy.pi/10)
	dort("PI^2", sympy.pi**2)
	dort("e / 3", sympy.E / 3)
	doit('0.0', 0)
	doit('.0', 0)
	doit('01', 1)
	doit('00', 0)
	doit('0.1', sympy.Number(1) / sympy.Number(10))

def test_math_functions():
	dort('sin(37)', sympy.sin(37))
	dort('cos(38)', sympy.cos(38))
	dort('tan(38)', sympy.tan(38))
	dort('sec(39)', sympy.sec(39))
	dort('csc(40)', sympy.csc(40))
	dort('cot(41)', sympy.cot(41))
	dort('asin(42)', sympy.asin(42))
	dort('acos(43)', sympy.acos(43))
	dort('atan(44)', sympy.atan(44))
	dort('asec(45)', sympy.asec(45))
	dort('acsc(46)', sympy.acsc(46))
	dort('acot(47)', sympy.acot(47))
	dort('sind(37)', sympy.sin(37 * sympy.pi / sympy.Number(180)))
	dort('cosd(38)', sympy.cos(38 * sympy.pi / sympy.Number(180)))
	dort('tand(38)', sympy.tan(38 * sympy.pi / sympy.Number(180)))
	dort('secd(39)', sympy.sec(39 * sympy.pi / sympy.Number(180)))
	dort('cscd(40)', sympy.csc(40 * sympy.pi / sympy.Number(180)))
	dort('cotd(41)', sympy.cot(41 * sympy.pi / sympy.Number(180)))
	dort('asind(42)', sympy.asin(42) * sympy.Number(180) / sympy.pi)
	dort('acosd(43)', sympy.acos(43) * sympy.Number(180) / sympy.pi)
	dort('atand(44)', sympy.atan(44) * sympy.Number(180) / sympy.pi)
	dort('asecd(45)', sympy.asec(45) * sympy.Number(180) / sympy.pi)
	dort('acscd(46)', sympy.acsc(46) * sympy.Number(180) / sympy.pi)
	dort('acotd(47)', sympy.acot(47) * sympy.Number(180) / sympy.pi)
	dort('sinh(4)', sympy.sinh(4))
	dort('cosh(5)', sympy.cosh(5))
	dort('tanh(6)', sympy.tanh(6))
	dort('asinh(4)', sympy.asinh(4))
	dort('acosh(5)', sympy.acosh(5))
	dort('atanh(6)', sympy.atanh(6))	
	dort('int(E)', int(sympy.E))
	dort('int(-E)', int(-sympy.E))

def test_power():
	doit("2^3^2", 2**3**2)
	doit("2^3+2", 2**3+2)
	doit("2^9", 2**9)
	dort("E^PI", sympy.E**sympy.pi)

# def test_mixed():
# 	doit('round(sin(20))!', sympy.factorial(round(sympy.sin(20))))
# 	doit('2 * 3!', 2 * sympy.factorial(3))
# 	doit('(2 * 3)!', sympy.factorial(2 * 3))

def test_logarithms():
	dort('log(5)', sympy.log(5, 10))
	dort('ln(5)', sympy.log(5))
	dort('ln(e)', 1)
	dort('ln(-3)', sympy.log(-3))
	dort('log(-3)', sympy.log(-3, 10))

def test_unicode():
	doit('3×2', 6)
	doit('6÷2', 3)
	dort('π', sympy.pi)
	dort('τ', 2 * sympy.pi)
	doit('5*0', 0)

# def test_dice_rolling():
# 	repeat('d6', 1, 6)
# 	repeat('2d6', 2, 12)
# 	repeat('8d9', 9, 8 * 9)
# 	repeat('d4 * d4', 1, 16)
# 	repeat('sin(d1000)', -1, 1)
# 	throws('d0')
# 	throws('10000d10000')

def test_factorial():
	for i in range(0, 10):
		doit('{}!'.format(i), sympy.factorial(i))
	for i in range(1, 10):
		dort('gamma({})'.format(i), sympy.gamma(i))
	doit('4.5!', sympy.gamma(sympy.Rational(9, 2) + 1))
	dort('gamma(5) - 5!', -96)
	throws('(-1)!')
	doit('300!', sympy.factorial(300))
	# throws('301!')

def test_problems():
	throws('nothing')

def test_equality():
	doit('1 < 2', True)
	doit('1 < 2 < 3', True)
	doit('1 < 2 > 1', True)
	doit('1 < 2 > 3', False)
	doit('1 < 2 > 3 < 4', False)
	doit('1 == 1', True)
	doit('1 != 1', False)
	doit('1 == 2', False)
	doit('1 != 2', True)
	doit('1 < 2 < 3 < 4 <= 4 >= 2 == 2 < 5', True)
	doit('1 < 2 && 3 < 4', True)
	doit('1 < 0 || 3 < 4', True)
	doit('3 == 3 && 2 == 2', True)

def test_assignment():
	doit('x = 2', None)
	doit('x = 2, y = 3', None)
	doit('a = 2, a', 2)
	doit('A = 2, a', 2)
	doit('a = 2, A', 2)
	doit('A = 2, A', 2)
	doit('x = 2, y = 3, x * y', 6)
	doit('f = (() -> f)', None)

def test_functions():
	doit('double = (x) -> x * 2, double(3)', 6)
	doit('multiply = (x, y) -> x * y, multiply(4, 5)', 20)
	doit('double (x) = x * 2, double(3)', 6)
	doit('multiply (x, y) = x * y, multiply(4, 5)', 20)
	doit('f = (n) -> if (n < 2, 1, f(n - 1) + f(n - 2)), f(5)', 8)
	doit('f = (n) -> if (n < 2, 1, f(n - 1) + f(n - 2)), f(50)', 20365011074)
	doit('if(0, 0, 0)', 0)
	compile_fail('if(0, 0)')
	compile_fail('if(0, 0, 0, 0)')
	doit('f = (x) -> x, t = f(5), 1 + f(5)', 6)
	doit('(x -> x * 2)(8)', 16)
	doit('f = x -> x * 3, f(3)', 9)

def test_function_creation():
	doit('f = x -> x * 2, f(3)', 6)
	doit('f(x) = x * 2, f(3)', 6)
	doit('f = (x y) -> x + y, f(1, 2)', 3)
	doit('f(x y) = x + y, f(1, 2)', 3)

def test_macros():
	doit('((x) ~> x())(5)', 5)
	doit('(x ~> x())(5 + 6)', 11)

def test_logic():
	dort('true  && true',  True)
	dort('true  && false', False)
	dort('false && true',  False)
	dort('false && false', False)
	dort('true  || true',  True)
	dort('true  || false', True)
	dort('false || true',  True)
	dort('false || false', False)
	doit('1 && 1 || 1 && 0', True)
	doit('0 || 1 && 1 || 0', True)
	doit('0 || 1 && 0 || 0', False)
	doit('!0', 1)
	doit('!1', 0)
	doit('!!0', 0)
	doit('!!1', 1)
	doit('!!3!!', 1)

def test_short_circuit():
	doit('1 || x', 1)
	doit('1 || x || x || x', 1)
	doit('0 && x', 0)
	doit('0 && x && x', 0)
	throws('0 || x')
	throws('1 && x')

def test_gcd():
	dort('gcd(8, 6)', 2)
	dort('lcm(3, 2)', 6)

def test_type_checking():
# 	doit('is_real(1)', True)
# 	doit('is_real(2.5)', True)
# 	doit('is_real(3i)', False)
# 	doit('is_real(sin)', False)
# 	doit('is_real((x) -> x)', False)
# 	doit('is_real((x) ~> x)', False)

# 	doit('is_complex(1)', False)
# 	doit('is_complex(2.5)', False)
# 	doit('is_complex(3i)', True)
# 	doit('is_complex(sin)', False)
# 	doit('is_complex((x) -> x)', False)
# 	doit('is_complex((x) ~> x)', False)

	dort('is_function(1)', False)
	dort('is_function(2.5)', False)
	dort('is_function(3i)', False)
	dort('is_function(sin)', True)
	dort('is_function((x) -> x)', True)
	dort('is_function((x) ~> x)', True)
	dort('is_function(((x) ~> x)(1))', True)
	dort('is_function(((x) ~> x)(1)())', False)

def test_large_numbers():
	doit('200! / 3', sympy.factorial(200) / sympy.Number(3))
	# throws('200! / 3.2')

def test_variadic_function():
	doit('((n, a.) -> a(n))(0, 7, 8, 9)', 7)
	doit('((n, a.) -> a(n))(1, 7, 8, 9)', 8)
	doit('((a.) -> a(4) + 2)(0, 1, 2, 3, 4, 5, 7, 8, 9)', 6)
	doit('list = (x.) -> x, list(9, 8, 7, 6, 5)', Ignore)
	dort('''
		_min2 = (x, y) -> if (x < y, x, y),
		_minV = (l, i) -> if (i == length(l) - 1, l(i), _min2(l(i), _minV(l, i + 1))),
		_min = (x.) -> _minV(x, 0),
		_min(7, 3, 6, 9)
	''', 3)

def test_argument_expansion():
	dort('sum(expand(array(1, 2)))', 3)
	throws('msum = (x, y) ~> x() + y(), msum(expand(array(1, 2)))')

def test_superscript():
	doit('2²', 4)
	doit('2²²', 4194304)
	doit('2² ²', 16)
	doit('3³ ⁴', (3 ** 3) ** 4)
	doit('(3³)⁴', (3 ** 3) ** 4)

def test_if_statement():
	doit('if (0, 3, 4)', 4)
	doit('if (1, 3, 4)', 3)
	doit('if (2, 3, 4)', 3)
	dort('x = if, x(0, 3, 4)', 4)
	dort('x = if, x(1, 3, 4)', 3)
	dort('x = if, x(2, 3, 4)', 3)

def test_map():
	dort("' \\ map((x) -> x * 2, list(0, 1, 2, 3, 4, 5))", 2)
	dort("' \\ \\ \\ \\ map((x) -> x * 2, list(0, 1, 2, 3, 4, 5))", 8)
	dort("' \\ map((x) ~> x() * 2, list(0, 1, 2, 3, 4, 5))", 2)
	dort("' \\ \\ \\ map(sin, list(0, 1, 2, 3, 4))", sympy.sin(3))
	dort("' \\ map((x) -> x * 2, range(0, 6))", 2)
	dort("' \\ \\ \\ \\ map((x) -> x * 2, range(0, 6))", 8)
	throws("' \\ \\ \\ \\ map((a, b) -> a + b, list(0, 1, 2, 3, 4, 5))")
	dort("length(list(1, 2, 3))", 3)
	dort("f = (x) -> x * 2, length(map(f, list()))", 0)

def test_foldl():
	dort('foldl((a, b) -> a + b, 0, list(0, 1, 2, 3, 4))', 10)
	dort('foldl(sum, 0, range(0, 5))', 10)
	throws('foldl((a, b) -> a + b, list())')
	throws('foldl(3, 4)')
	throws('foldl(() -> f, list(1, 2))')
	dort('msum = (x, y) ~> x() + y(), foldl(msum, 0, list(1, 2, 3, 4))', 10)

def test_filter():
	dort('''
		is_even = (x) -> (x ~mod 2 == 0),
		length(filter(is_even, range(0, 100)))
	''', 50)
	dort('''
		is_small = (x) ~> x() < 5,
		length(filter(is_small, range(0, 100)))
	''', 5)

def test_range():
	# for i in range(0, 5):
	# 	dort('range(0, 5)({})'.format(i), i)
	# 	dort('range(10, 20)({})'.format(i), i + 10)
	dort('length(range(0, 5))', 5)
	dort('length(range(8, 10))', 2)
	dort('length(range(7, 7))', 0)
	# throws('range(5, 4)')

def test_invalid_syntax():
	parse_fail('= == =')
	parse_fail('== = ==')
	parse_fail('= = =')
	parse_fail('== == ==')
	parse_fail('3 -> 3')
	parse_fail('[] -> 3')
	parse_fail('-> -> x')
	parse_fail('f(x) -> x')

def test_compile_failures():
	compile_fail('(if) -> 0')
	compile_fail('(map) -> 0')
	compile_fail('(reduce) -> 0')
	compile_fail('(filter) -> 0')
	compile_fail('if = 0')
	compile_fail('map = 0')
	compile_fail('reduce = 0')
	compile_fail('filter = 0')

def test_errors():
	# throws('e^900')
	throws('sqrt(() -> 0)')
	# throws('10*2^6643')
	compile_fail('if (true, 8)')
	throws('low(1, 1)')
	throws('cos(true)')
	throws('sin(false)')

def test_trig():
	dort('sin(0)', 0)
	dort('cos(pi)', -1)
	dort('sin(8)', sympy.sin(8))
	dort('sin(8i+3)', sympy.sin(3+sympy.Number(8) * sympy.I))
	dort('atan(0.1)', sympy.atan(sympy.Rational(1, 10)))

def test_commaless():
	dort('sum(1 2)', 3)
	dort('sum(1 (1 + 1))', 3)

def test_strings():
	doit(';a', 'a')
	doit(';\\;', ';')
	doit(';\\\\', '\\')
	doit('"Hello"', "Hello")
	doit('\'"Hello"', 'H')
	doit('\\"Hello"', 'ello')
	doit(';a:; :"string"', "a string")

	tokenization_fail('"a')

	doit('“Hello”', "Hello")
	tokenization_fail('“a“b”c”')
	tokenization_fail('“a“')
	tokenization_fail('”a”')

def test_lists():
	doit("'[1 2 3]", 1)
	doit("'\\[1 2 3]", 2)
	doit("'\\\\[1 2 3]", 3)
	dort("length([1 2 3])", 3)
	# dort("length(.)", 0)
	dort("length([])", 0)
	dort("'\\\\\\\\join([1 2 3] [4 5 6])", 5)

def test_percentage():
	doit('100%', 1)
	doit('1%', 0.01)
	doit('1 + 1%', 1.01)

def test_try_catch():
	doit('try(1, x)', 1)
	doit('try(x, 2)', 2)
	doit('try(x, 2, 3, 4, 5)', 2)
	doit('try(x, x, 3, 4, 5)', 3)
	doit('try(x, 8, x)', 8)

def test_unicode():
	tokens = calculator.parser.tokenizer(';🐱', calculator.parser.TOKEN_SPEC)
	strings = list(map(lambda x: x['string'], tokens))
	assert strings == ['', ';🐱', '']

	result = calculator.calculate(';🐱')
	assert isinstance(result, calculator.functions.Glyph)
	assert result.value == '🐱'
	assert calculator.formatter.format(result) == '🐱'

	doformatted(';🐱', '🐱')
	doformatted(';🐶 : ;🦊 :[]', '"🐶🦊"')
	doformatted(';🐶 : ;🦊 :[]', '"🐶🦊"')
	doformatted('"🐶🦊"', '"🐶🦊"')
	doformatted('ord(;🐱)', '128\u201A049')
	doformatted('chr(ord(;🐱))', '🐱')

def test_small_floats():
	doformatted('0.2', '1/5')
	doformatted('0.1 + 0.2 - 0.3', '0')
	doformatted('3.14', '157/50')

def test_operator_fuctions():
	dort('sum(1, 2)', 3)
	dort('sum(5783, 3857)', 5783 + 3857)
	dort('dif(5, 2)', 3)
	dort('dif(4853, 246745)', 4853 - 246745)
	dort('mul(4, 7)', 4 * 7)
	dort('mul(37563, -35728)', 37563 * -35728)
	dort('div(8, 4)', 2)
	dort('div(5, 1)', 5)
	dort('mod(7, 3)', 1)

def test_object_equality():
	doit('[] == []', True)
	dort('[1, 2, 3] == \\range(0 4)', True)
	dort('[1, 2, 3] == range(0 4)', False)
	doit('["foo"] != [1 2 3]', True)
	doit('2^100 == 2^101/2', True)
	doit('"dx is the best xd" == "dx is the best xd"', True)
	doit('\'"DXSmiley" == \'"Discord"', True)
	doit('"" == ""', True)
	doit('"d" == \\"d"', False)
	doit('[1] == [1]', True)
	doit('[100] == [1000/10]', True)
	doit('[1 2 3] == [1 2 3]', True)
	doit('[0 0 0] == [1 1 1]', False)
	doit('[[1 2] 3 [4 5]] == [[1 2] 3 [4 5]]', True)
	throws('1 == []')
	throws('[] == 1')
	throws('[[]] == [1]')
	throws('[1] == [[]]')

def test_object_ordering():
	doit('[0] < [1]', True)
	doit('[0] < [1] < [2]', True)
	doit('[6, 0] < [3, 2]', False)
	doit('[0] <= [0]', True)
	doit('"a" < "b"', True)
	doit('"a" <= "b"', True)
	doit('"a" > "b"', False)
	doit('"a" >= "b"', False)
	doit('"text" <= "text that is longer"', True)
	doit('"text" <  "text that is longer"', True)
	doit('"text" >= "text that is longer"', False)
	doit('"text" >  "text that is longer"', False)
	throws('[0] <  [[]]')
	throws('[0] <= [[]]')
	throws('[0] >  [[]]')
	throws('[0] >= [[]]')
	throws('[[]] <  [0]')
	throws('[[]] <= [0]')
	throws('[[]] >  [0]')
	throws('[[]] >= [0]')

def test_floats():
	doit('0.1', sympy.Rational(1, 10))
	doit('0.01', sympy.Rational(1, 100))
	doit('1e-1', sympy.Rational(1, 10))
	doit('1e-2', sympy.Rational(1, 100))
	doit('1e1', 10)
	doit('1e2', 100)
	doit('1e+1', 10)
	doit('1e+2', 100)

def test_unicode_operators():
	doit('1 ≤ 1', True)
	doit('1 ≤ 2', True)
	doit('2 ≤ 1', False)
	doit('1 ≯ 1', True)
	doit('1 ≯ 2', True)
	doit('2 ≯ 1', False)
	doit('1 ≥ 1', True)
	doit('2 ≥ 1', True)
	doit('1 ≥ 2', False)
	doit('1 ≮ 1', True)
	doit('1 ≮ 2', False)
	doit('2 ≮ 1', True)
	doit('1 ≠ 1', False)
	doit('1 ≠ 2', True)
	doit('1 ≤ 2 ≤ 3', True)
	doit('4 ≤ 2 ≤ 3', False)
	doit('1 ≤ 2 ≤ 1', False)

