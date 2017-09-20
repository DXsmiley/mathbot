import json
import asyncio
import math
import random

import calculator.runtime as runtime
import calculator.bytecode as bytecode
from calculator.errors import EvaluationError
from calculator.attempt6 import parse
from calculator.functions import *
import calculator.operators as operators


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


class IndexedScope:

	def __init__(self, superscope, size, values):
		self.superscope = superscope
		assert(len(values) == size)
		self.values = values

	def get(scope, index, depth):
		while depth > 0:
			scope = scope.superscope
			depth -= 1
		assert(scope.values[index] != None)
		return scope.values[index]

	def set(scope, index, depth, value):
		while depth > 0:
			scope = scope.superscope
			depth -= 1
		while len(scope.values) <= index:
			scope.values.append(None)
		scope.values[index] = value

	def __repr__(self):
		return 'indexed-scope'



def DoNothing():
	pass


def rolldie(times, faces):
	if isinstance(times, float):
		times = int(times)
	if isinstance(faces, float):
		faces = int(faces)
	if not isinstance(times, int) or not isinstance(faces, int):
		raise EvaluationError('Cannot roll {} dice with {} faces'.format(
			calculator.errors.format_value(times),
			calculator.errors.format_value(faces)
		))
	if times < 1:
		return 0
	if times > 1000:
		raise EvaluationError('Cannot roll more than 1000 dice')
	if faces < 1:
		raise EvaluationError('Cannot roll die with less than one face')
	if isinstance(faces, float) and not faces.is_integer():
		raise EvaluationError('Cannot roll die with fractional number of faces')
	return sum(random.randint(1, faces) for i in range(times))


class Interpereter:

	def __init__(self, bytes, trace = False, builder = None):
		self.builder = builder
		self.trace = trace
		self.bytes = bytes
		self.place = 0
		self.stack = [None]
		self.root_scope = IndexedScope(None, 0, [])
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
			b.BIN_DIE: self.inst_bin_die,
			b.BIN_AND: self.inst_and,
			b.BIN_OR_: self.inst_or,
			b.JUMP_IF_MACRO: self.inst_jump_if_macro,
			b.DEMACROIFY: self.inst_demacroify,
			b.STORE_DEMACROD: self.inst_store_demacrod,
			b.ARG_LIST_END: self.inst_arg_list_end,
			b.ASSIGNMENT: self.inst_assignment,
			b.WORD: self.inst_word,
			b.ACCESS_LOCAL: self.inst_access_local,
			b.ACCESS_GLOBAL: self.inst_access_gobal,
			b.ACCESS_SEMI: self.inst_access_semi,
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
			b.UNR_NOT: self.inst_unr_not,
			b.STORE_IN_CACHE: self.inst_store_in_cache
		}

	def prepare_extra_code(self, ast, ready_to_run = True):
		if self.builder is None:
			if len(self.bytes) == 0:
				raise Exception('Attempted to add additional code to an environment without a builder specified.')
			self.builder = bytecode.CodeBuilder()
		if ready_to_run:
			self.place = len(self.bytes)
			self.stack = [None]
		self.builder.bytecodeify(ast)
		self.bytes = self.builder.dump()

	@property
	def head(self):
		'''Return the instruction under the playhead'''
		return self.bytes[self.place]

	@property
	def top(self):
		'''Return the item on the top of the stack'''
		return self.stack[-1]

	def pop(self):
		'''Remove the item from the top of the stack and return it'''
		return self.stack.pop()

	def push(self, item):
		'''Push an item to the stop of the stack'''
		self.stack.append(item)

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
		if self.trace:
			print(self.place, self.head, self.stack)
		inst = self.switch_dictionary.get(self.head)
		if inst is None:
			print('Tried to run unknown instruction:', self.head)
			raise EvaluationError('Tried to run unknown instruction: ' + repr(self.head))
		else:
			inst()
		self.place += 1

	def inst_constant(self):
		self.place += 1
		self.stack.append(self.head)

	def binary_op(op):
		def internal(self):
			self.stack.append(op(self.stack.pop(), self.stack.pop()))
		return internal

	inst_add = binary_op(operators.operator_add)
	inst_mul = binary_op(operators.operator_multiply)
	inst_sub = binary_op(operators.operator_subtract)
	inst_div = binary_op(operators.operator_division)
	inst_mod = binary_op(operators.operator_modulo)
	inst_pow = binary_op(operators.operator_power)
	inst_bin_less = binary_op(operators.operator_less)
	inst_bin_more = binary_op(operators.operator_more)
	inst_bin_l_eq = binary_op(operators.operator_less_equal)
	inst_bin_m_eq = binary_op(operators.operator_more_equal)
	inst_bin_equl = binary_op(operators.operator_equal)
	inst_bin_n_eq = binary_op(operators.operator_not_equal)
	inst_bin_die = binary_op(rolldie)
	inst_and = binary_op(lambda a, b: int(a and b))
	inst_or = binary_op(lambda a, b: int(a or b))

	def inst_unr_min(self):
		self.stack.append(
			operators.operator_subtract(
				0,
				self.stack.pop()
			)
		)

	def inst_unr_fac(self):
		self.stack.append(operators.function_factorial(self.stack.pop()))

	def inst_unr_not(self):
		self.stack.append(int(not self.stack.pop()))

	def inst_comparison(comparator):
		def internal(self):
			r = self.stack.pop()
			l = self.stack.pop()
			x = int(comparator(l, r))
			self.stack[-1] &= x
			self.stack.append(r)
		return internal

	inst_cmp_less = inst_comparison(operators.operator_less)
	inst_cmp_more = inst_comparison(operators.operator_more)
	inst_cmp_l_eq = inst_comparison(operators.operator_less_equal)
	inst_cmp_m_eq = inst_comparison(operators.operator_more_equal)
	inst_cmp_equl = inst_comparison(operators.operator_equal)
	inst_cmp_n_eq = inst_comparison(operators.operator_not_equal)

	def inst_discard(self):
		self.stack.pop()

	def inst_jump_if_macro(self):
		self.place += 1
		if self.stack[-1].macro:
			self.place = self.head # Not -1 because it jumps to nothing

	def inst_demacroify(self):
		self.place += 1
		num_args = self.head
		processed = self.stack.pop()
		function = self.stack[- 1 - num_args]
		# print(self.place, self.stack, ':', function, processed, '/', num_args)
		# stack contains: function, arguments
		if processed < num_args and not function.macro:
			callme = self.stack[-1 - processed]
			# print(callme)
			self.stack.append(processed + 1)
			# Return here afterwards, next instruction is STORE_DEMACROD
			self.stack.append(self.place + 1)
			self.stack.append(self.current_scope)
			# print(self.stack)
			self.place = (callme.address + 3) - 1
		else:
			# print('DONE', self.stack)
			# Skip over the STORE_DEMACROD instruction
			self.place += 1

	def inst_store_demacrod(self):
		result = self.pop()
		processed = self.top
		self.stack[-1 - processed] = result
		# Jump back to the DEMACROIFY instruction
		self.place -= 3

	def inst_arg_list_end(self):
		# Look at the number of arguments
		self.place += 1
		stack_arg_count = self.head
		arguments = []
		for i in range(stack_arg_count):
			arg = self.stack.pop()
			if isinstance(arg, Expanded):
				arguments += arg.array.items
			else:
				arguments.append(arg)
		function = self.stack.pop()
		if isinstance(function, BuiltinFunction) or isinstance(function, Array):
			result = function(*arguments)
			self.stack.append(result)
			self.place += 1 # Skip the 'store in cache' instruction
		elif isinstance(function, Function):
			# Create the new scope in which to run the function
			addr = function.address
			num_parameters = self.bytes[addr + 1]
			parameters = [
				self.bytes[i] for i in
				range(addr + 2, addr + 2 + num_parameters)
			]
			variadic = self.bytes[addr + 2 + num_parameters]
			if variadic:
				if len(arguments) < num_parameters - 1:
					raise EvaluationError('Not enough arguments for variadic function {}'.format(function))
				main = arguments[:num_parameters - 1]
				extra = arguments[num_parameters - 1:]
				# scope_dict = {key: value for key, value in zip(parameters, main)}
				# scope_dict[parameters[-1]] = Array(extra)
				scope_array = main
				scope_array.append(Array(extra))
				new_scope = IndexedScope(function.scope, num_parameters, scope_array)
			else:
				if num_parameters != len(arguments):
					raise EvaluationError('Improper number of arguments for function {}'.format(function))
				if num_parameters == 0:
					new_scope = function.scope
				else:
					# new_scope = Scope(function.scope, {
					# 	key: value for key, value in zip(parameters, arguments)
					# })
					new_scope = IndexedScope(function.scope, num_parameters, arguments)
			cache_key = tuple(arguments)
			if cache_key in function.cache:
				self.stack.append(function.cache[cache_key])
				self.place += 1 # Skip the 'store in cache' instruction
			else:
				if function.macro:
					# Return here after the function is done but skip the STORE_IN_CACHE instruction
					self.stack.append(self.place + 2)
				else:
					# Required for storing the result in the result cache
					self.push(function)
					self.push(cache_key)
					# Return here after the function is done
					self.stack.append(self.place + 1)
				# Remember the current scope
				self.stack.append(self.current_scope)
				self.current_scope = new_scope
				self.place = (addr + 3 + num_parameters) - 1
		else:
			raise EvaluationError('{} is not a function'.format(function))

	def inst_word(self):
		assert(False)
		self.place += 1
		self.stack.append(self.current_scope[self.head])

	def inst_access_gobal(self):
		self.place += 1
		self.stack.append(self.root_scope.get(self.head, 0))

	def inst_access_local(self):
		self.place += 1
		self.stack.append(self.current_scope.get(self.head, 0))

	def inst_access_semi(self):
		self.stack.append(
			self.current_scope.get(
				self.bytes[self.place + 2],
				self.bytes[self.place + 1]
			)
		)
		self.place += 2

	def inst_assignment(self):
		value = self.stack.pop()
		self.place += 1
		name = self.head
		self.root_scope.set(name, 0, value)

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

	def inst_store_in_cache(self):
		# print(self.stack)
		value = self.stack.pop()
		cache_key = self.stack.pop()
		function = self.stack.pop()
		function.cache[cache_key] = value
		self.stack.append(value)


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
