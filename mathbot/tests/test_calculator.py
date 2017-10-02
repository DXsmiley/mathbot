import calculator
import pytest
import math

class Ignore: pass

def doit(equation, result):
	r = calculator.calculate(equation)
	assert result is Ignore or r == result

def repeat(equation, start, end):
	for i in range(100):
		r = calculator.calculate(equation)
		assert start <= r <= end

def unknown(equation):
	calculator.calculate(equation)

def throws(equation):
	with pytest.raises(calculator.errors.EvaluationError):
		calculator.calculate(equation)

def compile_fail(equation):
	with pytest.raises(calculator.errors.CompilationError):
		calculator.calculate(equation)

def test_negation():
	doit("9", 9)
	doit("-9", -9)
	# doit("--9", 9)
	doit("(9)", 9)
	doit("(-9)", -9)
	# doit("(--9)", 9)
	doit("-E", -math.e)
	doit('3-2', 1)
	doit('3 - 2', 1)

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
	doit('5 % 2', 1)
	doit('10 % 4', 2)
	throws('10 % 0')

def test_constants():
	doit("PI * PI / 10", math.pi * math.pi / 10)
	doit("PI*PI/10", math.pi*math.pi/10)
	doit("PI^2", math.pi**2)
	doit("e / 3", math.e / 3)

def test_functions():
	doit("round(PI^2)", round(math.pi**2))
	doit("sin(PI/2)", math.sin(math.pi/2))
	doit("int(E)", int(math.e))
	doit("int(-E)", int(-math.e))
	doit("round(E)", round(math.e))
	doit("round(-E)", round(-math.e))

def test_power():
	doit("2^3^2", 2**3**2)
	doit("2^3+2", 2**3+2)
	doit("2^9", 2**9)
	doit("E^PI", math.e**math.pi)

def test_mixed():
	doit('round(sin(20))!', math.factorial(round(math.sin(20))))
	doit('2 * 3!', 2 * math.factorial(3))
	doit('(2 * 3)!', math.factorial(2 * 3))

def test_logarithms():
	doit('log(5)', math.log10(5))
	doit('ln(5)', math.log(5))
	doit('ln(e)', 1)
	throws('ln(-3)')
	throws('log(-3)')

def test_unicode():
	doit('3×2', 6)
	doit('6÷2', 3)
	doit('π', math.pi)
	doit('5*0', 0)

def test_dice_rolling():
	repeat('d6', 1, 6)
	repeat('2d6', 2, 12)
	repeat('8d9', 9, 8 * 9)
	repeat('d4 * d4', 1, 16)
	repeat('sin(d1000)', -1, 1)
	throws('d0')
	throws('10000d10000')

def test_factorial():
	for i in range(0, 10):
		doit('{}!'.format(i), math.factorial(i))
	for i in range(1, 10):
		doit('gamma({})'.format(i), math.gamma(i))
	doit('4.5!', math.gamma(4.5 + 1))
	doit('gamma(5) - 5!', -96)
	throws('(-1)!')
	doit('300!', math.factorial(300))
	throws('301!')

def test_problems():
	throws('nothing')

def test_equality():
	doit('1 < 2', True)
	doit('1 < 2 < 3', True)
	doit('1 < 2 > 1', True)
	doit('1 < 2 > 3', False)
	doit('1 == 1', True)
	doit('1 != 1', False)
	doit('1 == 2', False)
	doit('1 != 2', True)
	doit('1 < 2 < 3 < 4 <= 4 >= 2 == 2 < 5', True)

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
	doit('product = (x, y) -> x * y, product(4, 5)', 20)
	doit('f = (n) -> if (n < 2, 1, f(n - 1) + f(n - 2)), f(5)', 8)
	doit('f = (n) -> if (n < 2, 1, f(n - 1) + f(n - 2)), f(50)', 20365011074)
	doit('if(0, 0, 0)', 0)
	compile_fail('if(0, 0)')
	compile_fail('if(0, 0, 0, 0)')

def test_macros():
	doit('((x) ~> x())(5)', 5)
	doit('((x) ~> x())(5 + 6)', 11)

def test_logic():
	doit('true  & true',  True)
	doit('true  & false', False)
	doit('false & true',  False)
	doit('false & false', False)
	doit('true  | true',  True)
	doit('true  | false', True)
	doit('false | true',  True)
	doit('false | false', False)
	doit('1 & 1 | 1 & 0', True)
	doit('0 | 1 & 1 | 0', True)
	doit('0 | 1 & 0 | 0', False)
	doit('!0', 1)
	doit('!1', 0)
	doit('!!0', 0)
	doit('!!1', 1)
	doit('!!3!!', 1)

def test_gcd():
	doit('gcd(8, 6)', 2)
	doit('lcm(3, 2)', 6)

def test_type_checking():
	doit('is_real(1)', True)
	doit('is_real(2.5)', True)
	doit('is_real(3i)', False)
	doit('is_real(sin)', False)
	doit('is_real((x) -> x)', False)
	doit('is_real((x) ~> x)', False)

	doit('is_complex(1)', False)
	doit('is_complex(2.5)', False)
	doit('is_complex(3i)', True)
	doit('is_complex(sin)', False)
	doit('is_complex((x) -> x)', False)
	doit('is_complex((x) ~> x)', False)

	doit('is_function(1)', False)
	doit('is_function(2.5)', False)
	doit('is_function(3i)', False)
	doit('is_function(sin)', True)
	doit('is_function((x) -> x)', True)
	doit('is_function((x) ~> x)', True)
	doit('is_function(((x) ~> x)(1))', True)
	doit('is_function(((x) ~> x)(1)())', False)

def test_large_numbers():
	doit('200! / 3', math.factorial(200) // 3)
	throws('200! / 3.2')

def test_variadic_function():
	doit('((n, a.) -> a(n))(0, 7, 8, 9)', 7)
	doit('((n, a.) -> a(n))(1, 7, 8, 9)', 8)
	doit('((a.) -> a(4) + 2)(0, 1, 2, 3, 4, 5, 7, 8, 9)', 6)
	doit('list = (x.) -> x, list(9, 8, 7, 6, 5)', Ignore)
	doit('''
		min2 = (x, y) -> if (x < y, x, y),
		minV = (l, i) -> if (i == length(l) - 1, l(i), min2(l(i), minV(l, i + 1))),
		min = (x.) -> minV(x, 0),
		min(7, 3, 6, 9)
	''', 3)

def test_argument_expansion():
	doit('sum = (x, y) -> x + y, array = (a.) -> a, sum(expand(array(1, 2)))', 3)
	throws('sum = (x, y) ~> x() + y(), array = (a.) -> a, sum(expand(array(1, 2)))')

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
	doit('x = if, x(0, 3, 4)', 4)
	doit('x = if, x(1, 3, 4)', 3)
	doit('x = if, x(2, 3, 4)', 3)

def test_map():
	doit('map((x) -> x * 2, array(0, 1, 2, 3, 4, 5))(1)', 2)
	doit('map((x) -> x * 2, array(0, 1, 2, 3, 4, 5))(4)', 8)
	throws('map((a, b) -> a + b, array(0, 1, 2, 3, 4, 5))(4)')

def test_reduce():
	doit('reduce((a, b) -> a + b, array(0, 1, 2, 3, 4))', 10)
	throws('reduce((a, b) -> a + b, array())')