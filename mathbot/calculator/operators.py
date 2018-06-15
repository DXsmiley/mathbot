import itertools
import operator
import math
import cmath
import sympy

import calculator.errors

DIGITS_LIMIT = 2000
MAXIMUM_INTEGER = 10 ** DIGITS_LIMIT
NUMBER = [int, float]
COMPLEX = [int, float, complex]

LIST_OF_NOTHING = ['nothing'] * 4

# Set of functions that call the asyncronous comparitors.
# Only __aeq__ and __alt__ should be implemented.

async def super_equals(a, b):
	if hasattr(a, '__aeq__'):
		return await a.__aeq__(b)
	if hasattr(b, '__aeq__'):
		return await b.__aeq__(a)
	return a == b

async def super_not_equals(a, b):
	return not (await super_equals(a, b))

async def super_less_than(a, b):
	if hasattr(a, '__alt__'):
		return await a.__alt__(b)
	return a < b

async def super_less_eq(a, b):
	return (await super_equals(a, b)) or (await super_less_than(a, b))

async def super_more_than(a, b):
	return await super_less_than(b, a)

async def super_more_eq(a, b):
	return (await super_equals(a, b)) or (await super_less_than(b, a))


class Overloadable:

	def __init__(self, error_format, format_defaults = []):
		self.error_format = error_format
		self.format_defaults = format_defaults
		self.dict = {}

	def overload(self, *types):
		def applier(function):
			mytypes = [i if isinstance(i, list) else [i] for i in types]
			for mask in itertools.product(*mytypes):
				if mask in self.dict:
					pass
					# print('Attempted to overload twice with', mask)
				else:
					self.dict[mask] = function
			return function
		return applier

	def __call__(self, *args):
		types = tuple(i.__class__ for i in args)
		try:
			return self.dict[types](*args)
		except KeyError:
			self.raise_error(*args)

	def raise_error(self, *args):
		reps = list(map(calculator.errors.format_value, args))
		raise calculator.errors.EvaluationError(self.error_format.format(*reps, *self.format_defaults, *LIST_OF_NOTHING))


def compose(*functions):
	assert(len(functions) > 0)
	functions = functions[::-1]
	def composed(*x):
		for f in functions:
			x = (f(*x),)
		return x[0]
	return composed


def cap_integer_size(x):
	if isinstance(x, int) and abs(x) > MAXIMUM_INTEGER:
		raise calculator.errors.EvaluationError('Integer overflow')
	return x


operator_add = Overloadable('Cannot add {0} to {1}')
operator_add.overload(COMPLEX, COMPLEX)(compose(cap_integer_size, operator.add))

operator_subtract = Overloadable('Cannot subtract {1} from {0}')
operator_subtract.overload(COMPLEX, COMPLEX)(compose(cap_integer_size, operator.sub))

operator_multiply = Overloadable('Cannot multiply {0} and {1}')

@operator_multiply.overload(int, int)
def multiply_ints(a, b):
	try:
		if a != 0 and b != 0:
			result_length = math.log10(abs(a)) + math.log10(abs(b))
			if result_length > DIGITS_LIMIT:
				return float(a) * float(b)
		return cap_integer_size(a * b)
	except OverflowError:
		raise calculator.errors.EvaluationError('Cannot multiply {} and {}. Result too large.'.format(a, b))
operator_multiply.overload(COMPLEX, COMPLEX)(operator.mul)

operator_modulo = Overloadable('Cannot perform modulo on {0} and {1}')
@operator_modulo.overload(int, int)
def modulo_ints(a, b):
	try:
		return a % b
	except (ZeroDivisionError, TypeError):
		raise calculator.errors.EvaluationError('Cannot divide {} by {}'.format(a, b))

operator_division = Overloadable('Cannot divide {0} by {1}')

@operator_division.overload(int, int)
def divison(a, b):
	try:
		if a % b == 0:
			return a // b
		return a / b
	except (ZeroDivisionError, TypeError):
		raise calculator.errors.EvaluationError('Cannot divide {} by {}'.format(a, b))
	except OverflowError:
		raise calculator.errors.EvaluationError('Diving {} by {} caused an overflow'.format(a, b))

@operator_division.overload(COMPLEX, COMPLEX)
def divison(a, b):
	try:
		return a / b
	except (ZeroDivisionError, TypeError):
		raise calculator.errors.EvaluationError('Cannot divide {} by {}'.format(a, b))
	except OverflowError:
		raise calculator.errors.EvaluationError('Diving {} by {} caused an overflow'.format(a, b))

operator_power = Overloadable('Cannot raise {0} to the power of {1}')

@operator_power.overload(int, int)
def power_int(base, exponent):
	if base == 0 and exponent == 0:
		raise calculator.errors.EvaluationError('Cannot raise 0 to the power of 0')
	if base == 0:
		return 0
	try:
		result_length = abs(exponent * math.log10(abs(base)))
		if result_length > DIGITS_LIMIT:
			return float(base) ** float(exponent)
		result = base ** exponent
		return cap_integer_size(result)
	except OverflowError:
		raise calculator.errors.EvaluationError('Overflow while calculating exponential')

@operator_power.overload(NUMBER, NUMBER)
def power_float(base, exponent):
	try:
		if base == 0 and exponent == 0:
			raise calculator.errors.EvaluationError('Cannot raise 0 to the power of 0')
		if base == 0:
			return 0
		result_length = abs(exponent * math.log10(abs(base)))
		if result_length > DIGITS_LIMIT:
			return base ** exponent
		if base < 0 and exponent == 0.5:
			return (-base) ** exponent * 1j
		result = base ** exponent
		return cap_integer_size(result)
	except OverflowError:
		raise calculator.errors.EvaluationError('Overflow while calculating exponential')

operator_less = Overloadable('Cannot compare {0} and {1}.')
operator_less.overload(NUMBER, NUMBER)(operator.lt)
operator_more = Overloadable('Cannot compare {0} and {1}.')
operator_more.overload(NUMBER, NUMBER)(operator.gt)
operator_less_equal = Overloadable('Cannot compare {0} and {1}.')
operator_less_equal.overload(NUMBER, NUMBER)(operator.le)
operator_more_equal = Overloadable('Cannot compare {0} and {1}.')
operator_more_equal.overload(NUMBER, NUMBER)(operator.ge)
operator_equal = operator.eq
operator_not_equal = operator.ne
# operator_equal = Overloadable('Cannot compare {0} and {1}.')
# operator_not_equal = Overloadable('Cannot compare {0} and {1}.')

@operator_power.overload(COMPLEX, COMPLEX)
def power_complex(base, exponent):
	try:
		return base ** exponent
	except OverflowError:
		raise calculator.errors.EvaluationError('Overflow while calculating exponential')
	except TypeError:
		raise calculator.errors.EvaluationError('Cannot raise {} to the power {}'.format(base, exponent))

function_factorial = Overloadable('Cannot perform the factorial function on {0}')
@function_factorial.overload(NUMBER)
def protected_factorial(x):
	return sympy.gamma(x + 1)
	# try:
	# 	if x > 300:
	# 		raise calculator.errors.EvaluationError('Cannot perform factorial on a number greater than 300')
	# 	if not float(x).is_integer() or x < 0:
	# 		try:
	# 			return sympy.Number(sympy.gamma(x + 1))
	# 		except ValueError:
	# 			raise calculator.errors.EvaluationError('Cannot perform factorial on a negative integer')
	# 		except OverflowError:
	# 			raise calculator.errors.EvaluationError('Overflow inside gamma function')
	# 	return sympy.Number(cap_integer_size(math.factorial(float(x))))
	# except TypeError:
	# 	raise calculator.errors.EvaluationError('Cannot perform factorial on {}'.format(x))

def log_func_real(number, base = 10):
	try:
		if base == 10:
			return math.log10(number)
		return math.log(number, base)
	except (ValueError, TypeError, ZeroDivisionError):
		raise calculator.errors.EvaluationError('Cannot calculate logarithm of {} with base {}'.format(number, base))

def log_func_complex(number, base = 10):
	try:
		if base == 10:
			return cmath.log10(number)
		return cmath.log(number, base)
	except (ValueError, TypeError, ZeroDivisionError):
		raise calculator.errors.EvaluationError('Cannot calculate logarithm of {} with base {}', number, base)

function_logarithm = Overloadable('Cannot perform the logarithm on {0} with base {1}', [10])
function_logarithm.overload(NUMBER, NUMBER)(log_func_real)
function_logarithm.overload(NUMBER)(lambda x : log_func_real(x))
function_logarithm.overload(complex, complex)(log_func_complex)
function_logarithm.overload(complex)(lambda x : log_func_complex(x))

function_gcd = Overloadable('Cannot get the greatest common divisor of {0} and {1}. Both arguments must be integers.')
function_gcd.overload(int, int)(math.gcd)

function_lcm = Overloadable('Cannot get the lowest common multiple of {0} and {1}. Both arguments must be integers.')
@function_lcm.overload(int, int)
def f_lcm(a, b):
	return (a * b) // math.gcd(a, b)
