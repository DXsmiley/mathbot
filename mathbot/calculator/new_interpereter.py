import json
import asyncio
import math

import calculator.runtime as runtime
import calculator.bytecode as bytecode
from calculator.errors import EvaluationError
from calculator.attempt6 import parse
from calculator.functions import *

class Scope:

	def __init__(self, previous, values, protected_names = None):
		self.values = values
		self.previous = previous
		self.protected_names = protected_names
		if self.protected_names is None and self.previous is not None:
			self.protected_names = self.previous.protected_names

	def __getitem__(self, key):
		try:
			return self.values[key]
		except KeyError:
			try:
				return self.previous[key]
			except TypeError:
				raise EvaluationError('Unknown name: {}'.format(key))

	def __setitem__(self, key, value):
		if self.protected_names is not None and key in self.protected_names:
			raise EvaluationError('\'{}\' is a protected constant and cannot be overridden'.format(key))
		# if key in self.values:
		# 	raise EvaluationError('{} has already been assigned in this scope'.format(key))
		self.values[key] = value

	def __repr__(self):
		return 'scope'

	# def __repr__(self):
	# 	return '{} -> {}'.format(repr(self.values), repr(self.previous))


def DoNothing():
	pass


class Interpereter:

	def __init__(self, bytes):
		self.bytes = bytes
		self.place = 0
		self.stack = [None]
		self.root_scope = Scope(None, {})
		self.current_scope = self.root_scope
		b = bytecode.I
		self.switch_dictionary = {
			b.NOTHING: DoNothing,
			b.CONSTANT: self.inst_constant,
			b.BIN_ADD: self.inst_add,
			b.BIN_SUB: self.inst_sub,
			b.BIN_MUL: self.inst_mul,
			b.BIN_DIV: self.inst_div,
			b.BIN_MOD: self.inst_mod,
			b.BIN_POW: self.inst_pow,
			b.JUMP_IF_MACRO: self.inst_jump_if_macro,
			b.ARG_LIST_END: self.inst_arg_list_end,
			b.ASSIGNMENT: self.inst_assignment,
			b.WORD: self.inst_word,
			b.FUNCTION_NORMAL: self.inst_function_normal,
			b.FUNCTION_MACRO: self.inst_function_macro,
			b.RETURN: self.inst_return,
			b.JUMP: self.inst_jump,
			b.JUMP_IF_TRUE: self.inst_jump_if_true,
			b.JUMP_IF_FALSE: self.inst_jump_if_false,
			b.BIN_LESS: self.inst_bin_less,
			b.BIN_MORE: self.inst_bin_more,
			b.BIN_L_EQ: self.inst_bin_l_eq,
			b.BIN_M_EQ: self.inst_bin_m_eq,
			b.BIN_EQUL: self.inst_bin_equl,
			b.BIN_N_EQ: self.inst_bin_n_eq,
			b.CMP_LESS: self.inst_cmp_less,
			b.CMP_MORE: self.inst_cmp_more,
			b.CMP_L_EQ: self.inst_cmp_l_eq,
			b.CMP_M_EQ: self.inst_cmp_m_eq,
			b.CMP_EQUL: self.inst_cmp_equl,
			b.CMP_N_EQ: self.inst_cmp_n_eq,
			b.DISCARD: self.inst_discard,
			b.UNR_MIN: self.inst_unr_min,
			b.UNR_FAC: self.inst_unr_fac,
		}

	def prepare_extra_code(self, ast):
		self.place = len(self.bytes)
		new_code = bytecode.build(ast, self.place)
		self.bytes += new_code
		self.stack = [None]

	@property
	def head(self):
		return self.bytes[self.place]

	def run(self, tick_limit = None, error_if_exhausted = False):
		try:
			if tick_limit is None:
				while self.head != bytecode.I.END:
					self.tick()
					# print(self.place, self.stack)
			else:
				while self.head != bytecode.I.END and tick_limit > 0:
					tick_limit -= 1
					self.tick()
					# print(self.place, self.stack)
		except Exception as e:
			raise EvaluationError(str(e))
		# print(self.stack)
		if error_if_exhausted and tick_limit == 0:
			raise EvaluationError('Execution timed out (by tick count)')
		return self.stack[-1]

	async def run_async(self):
		while self.head != bytecode.I.END:
			self.run(100)
			await asyncio.sleep(0)
		return self.stack[-1]

	def tick(self):
		inst = self.switch_dictionary.get(self.head)
		if inst is None:
			print('Tried to run unknown instruction:', self.head)
		else:
			inst()
		self.place += 1

	def inst_constant(self):
		self.place += 1
		self.stack.append(self.head)

	def inst_add(self):
		self.stack.append(self.stack.pop() + self.stack.pop())

	def inst_mul(self):
		self.stack.append(self.stack.pop() * self.stack.pop())

	def inst_sub(self):
		self.stack.append(self.stack.pop() - self.stack.pop())

	def inst_div(self):
		self.stack.append(self.stack.pop() / self.stack.pop())

	def inst_mod(self):
		self.stack.append(self.stack.pop() % self.stack.pop())

	def inst_pow(self):
		self.stack.append(self.stack.pop() ** self.stack.pop())

	def inst_unr_min(self):
		self.stack.append(-self.stack.pop())

	def inst_unr_fac(self):
		self.stack.append(math.factorial(self.stack.pop()))

	def inst_bin_less(self):
		self.stack.append(int(self.stack.pop() < self.stack.pop()))

	def inst_bin_more(self):
		self.stack.append(int(self.stack.pop() > self.stack.pop()))

	def inst_bin_l_eq(self):
		self.stack.append(int(self.stack.pop() <= self.stack.pop()))

	def inst_bin_m_eq(self):
		self.stack.append(int(self.stack.pop() >= self.stack.pop()))

	def inst_bin_equl(self):
		self.stack.append(int(self.stack.pop() == self.stack.pop()))

	def inst_bin_n_eq(self):
		self.stack.append(int(self.stack.pop() != self.stack.pop()))

	def inst_cmp_generic(comparator):
		def internal(self):
			r = self.stack.pop()
			l = self.stack.pop()
			x = int(comparator(l, r))
			self.stack[-1] &= x
			self.stack.append(r)
		return internal

	inst_cmp_less = inst_cmp_generic(lambda l, r: l < r)
	inst_cmp_more = inst_cmp_generic(lambda l, r: l > r)
	inst_cmp_l_eq = inst_cmp_generic(lambda l, r: l <= r)
	inst_cmp_m_eq = inst_cmp_generic(lambda l, r: l >= r)
	inst_cmp_equl = inst_cmp_generic(lambda l, r: l == r)
	inst_cmp_n_eq = inst_cmp_generic(lambda l, r: l != r)

	def inst_discard(self):
		self.stack.pop()

	def inst_jump_if_macro(self):
		self.place += 1
		if self.stack[-1].macro:
			self.place = self.head # Not -1 because it jumps to nothing

	def inst_arg_list_end(self):
		# Look at the number of arguments
		self.place += 1
		num_arguments = self.head
		arguments = []
		for i in range(num_arguments):
			arguments.append(self.stack.pop())
		function = self.stack.pop()
		if isinstance(function, BuiltinFunction) or isinstance(function, Array):
			result = function(*arguments)
			self.stack.append(result)
		elif isinstance(function, Function):
			# Push the current location and scope so we can jump back to it
			self.stack.append(self.place + 1)
			self.stack.append(self.current_scope)
			# Create the new scope in which to run the function
			addr = function.address
			num_parameters = self.bytes[addr + 1]
			parameters = [
				self.bytes[i] for i in
				range(addr + 2, addr + 2 + num_parameters)
			]
			variadic = self.bytes[addr + 1 + num_parameters]
			if variadic:
				if num_arguments < num_parameters - 1:
					raise EvaluationError('Not enough arguments for variadic function {}'.format(function))
				main = arguments[:num_parameters - 1]
				extra = arguments[num_parameters - 1:]
				scope_dict = {key: value for key, value in zip(parameters, main)}
				scope_dict[parameters[-1]] = Array(extra)
				new_scope = Scope(function.scope, scope_dict)
			else:
				if num_parameters != num_arguments:
					raise EvaluationError('Improper number of arguments for function {}'.format(function))
				if num_parameters == 0:
					new_scope = function.scope
				else:
					new_scope = Scope(function.scope, {
						key: value for key, value in zip(parameters, arguments)
					})
			self.current_scope = new_scope
			self.place = (addr + 3 + num_parameters) - 1
		else:
			raise EvaluationError('{} is not a function'.format(function))

	def inst_word(self):
		self.place += 1
		self.stack.append(self.current_scope[self.head])

	def inst_assignment(self):
		value = self.stack.pop()
		self.place += 1
		name = self.head
		self.current_scope[name] = value

	def inst_function_normal(self):
		self.place += 1
		self.stack.append(Function(self.head, self.current_scope, False))

	def inst_function_macro(self):
		self.place += 1
		self.stack.append(Function(self.head, self.current_scope, True))

	def inst_return(self):
		result = self.stack.pop()
		self.current_scope = self.stack.pop()
		self.place = self.stack.pop() - 1
		self.stack.append(result)

	def inst_jump(self):
		self.place += 1
		self.place = self.head - 1

	def inst_jump_if_true(self):
		self.place += 1
		if self.stack.pop():
			self.place = self.head - 1

	def inst_jump_if_false(self):
		self.place += 1
		if not self.stack.pop():
			self.place = self.head - 1


def test(string):
	# print('=========================================')
	# print('   ', string)
	# print('=========================================')
	tokens, ast = parse(string)
	# print(json.dumps(ast, indent = 4))
	bytes = bytecode.build({'#': 'program', 'items': [ast]})
	bytes = runtime.wrap_with_runtime(
		bytecode.CodeBuilder(),
		{'#': 'program', 'items': [ast]}
	)
	# for index, byte in enumerate(bytes):
	# 	print('{:3d} - {}'.format(index, byte))
	vm = Interpereter(bytes)
	return vm.run(tick_limit = 10000, error_if_exhausted = True)


if __name__ == '__main__':
	test('1 + 2')
	test('x = 1, y = x + 2, x + y')
	test('() -> 2')
	test('(x) -> 2 * x')
	test('t = (x) -> 3 * x, t(2) + 4')
	test('diff = (a, b, c) -> a - b - c, diff(1, 2, 3)')
	test('diff = (a, b, c) ~> a() - b() - c(), diff(1, 2, 3)')
	test('if(0, 3, 4)')
	test('if(1, 3, 4)')
	# test('sin(3)')
