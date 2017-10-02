import json
import asyncio
import math
import random

import calculator.runtime as runtime
import calculator.bytecode as bytecode
import calculator.errors
from calculator.errors import EvaluationError
from calculator.parser import parse
from calculator.functions import *
import calculator.operators as operators


class ScopeMissedError(Exception):
	pass


class IndexedScope:

	# NOTE: Not really sure why I have both size and values here. 
	def __init__(self, superscope, size, values):
		self.superscope = superscope
		if size != len(values):
			raise calculator.errors.SystemError('Attempted to create a scope with number of values unequal to the size')
		self.values = values

	def get(scope, index, depth):
		while depth > 0:
			scope = scope.superscope
			depth -= 1
		if index >= len(scope.values) or scope.values[index] == None:
			raise ScopeMissedError
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


def do_nothing():
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
			b.NOTHING: do_nothing,
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
			b.ACCESS_ARRAY_ELEMENT: self.inst_access_array_element,
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
			b.STORE_IN_CACHE: self.inst_store_in_cache,
			b.SPECIAL_MAP: self.inst_special_map,
			b.SPECIAL_MAP_STORE: self.inst_special_map_store,
			b.CONSTANT_EMPTY_ARRAY: self.inst_constant_empty_array,
			b.SPECIAL_REDUCE: self.inst_special_reduce,
			b.SPECIAL_REDUCE_STORE: self.inst_special_reduce_store,
			b.DUPLICATE: self.inst_duplicate
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

	def pop_n(self, count):
		''' Remove n items from the top of the stack and return them
			The first item in the list comes from the top of the stack
		'''
		return [self.stack.pop() for i in range(count)]

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
		except EvaluationError as e:
			raise e
		except Exception as e:
			raise e
		# print(self.stack)
		if error_if_exhausted and tick_limit == 0:
			raise EvaluationError('Execution timed out (by tick count)')
		if len(self.stack) > 2:
			raise SystemError('Execution finished with extra items on the stack. Is there a leak?')
		return self.top

	async def run_async(self):
		while self.head != bytecode.I.END:
			self.run(100)
			await asyncio.sleep(0)
		return self.top

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
		self.push(self.head)

	def inst_constant_empty_array(self):
		self.push(Array([]))

	def inst_duplicate(self):
		self.push(self.top)

	def binary_op(op):
		def internal(self):
			self.push(op(self.pop(), self.pop()))
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
	inst_and = binary_op(lambda a, b: int(bool(a) and bool(b)))
	inst_or = binary_op(lambda a, b: int(bool(a) or bool(b)))

	def inst_unr_min(self):
		self.push(
			operators.operator_subtract(
				0,
				self.pop()
			)
		)

	def inst_unr_fac(self):
		self.push(operators.function_factorial(self.pop()))

	def inst_unr_not(self):
		self.push(int(not bool(self.pop())))

	def inst_comparison(comparator):
		def internal(self):
			r = self.pop()
			l = self.pop()
			x = int(comparator(l, r))
			self.stack[-1] &= x
			self.push(r)
		return internal

	inst_cmp_less = inst_comparison(operators.operator_less)
	inst_cmp_more = inst_comparison(operators.operator_more)
	inst_cmp_l_eq = inst_comparison(operators.operator_less_equal)
	inst_cmp_m_eq = inst_comparison(operators.operator_more_equal)
	inst_cmp_equl = inst_comparison(operators.operator_equal)
	inst_cmp_n_eq = inst_comparison(operators.operator_not_equal)

	def inst_discard(self):
		self.pop()

	def inst_jump_if_macro(self):
		self.place += 1
		if self.top.macro:
			self.place = self.head # Not -1 because it jumps to nothing

	def inst_demacroify(self):
		self.place += 1
		num_args = self.head
		processed = self.pop()
		function = self.stack[- 1 - num_args]
		# print(self.place, self.stack, ':', function, processed, '/', num_args)
		# stack contains: function, arguments
		if processed < num_args and not function.macro:
			callme = self.stack[-1 - processed]
			# print(callme)
			self.push(processed + 1)
			# Return here afterwards, next instruction is STORE_DEMACROD
			self.push(self.place + 1)
			self.push(self.current_scope)
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
			arg = self.pop()
			if isinstance(arg, Expanded):
				for i in arg.arrays:
					arguments += i.items
			else:
				arguments.append(arg)
		function = self.pop()
		self.call_function(function, arguments, self.place + 1)

	def inst_word(self):
		assert(False)
		self.place += 1
		self.push(self.current_scope[self.head])

	def inst_access_gobal(self):
		self.place += 1
		index = self.head
		self.place += 1
		try:
			self.push(self.root_scope.get(index, 0))
		except ScopeMissedError:
			raise EvaluationError('Failed to access variable "{}"'.format(self.head))

	def inst_access_local(self):
		self.place += 1
		self.push(self.current_scope.get(self.head, 0))

	def inst_access_semi(self):
		self.push(
			self.current_scope.get(
				self.bytes[self.place + 2],
				self.bytes[self.place + 1]
			)
		)
		self.place += 2

	def inst_access_array_element(self):
		index = self.pop()
		array = self.pop()
		if not isinstance(array, Array):
			raise EvaluationError('Cannot access element of non-array object')
		if not isinstance(index, int):
			raise EvaluationError('Cannot access non-integer element of an array')
		if index < 0 or index >= len(array):
			raise EvaluationError('Attempted to access out-of-bounds element of an array')
		self.push(array.items[index])

	def inst_assignment(self):
		value = self.pop()
		self.place += 1
		name = self.head
		self.root_scope.set(name, 0, value)

	def inst_function_normal(self):
		self.place += 1
		self.push(Function(self.head, self.current_scope, False))

	def inst_function_macro(self):
		self.place += 1
		self.push(Function(self.head, self.current_scope, True))

	def inst_return(self):
		result = self.pop()
		self.current_scope = self.pop()
		self.place = self.pop() - 1
		self.push(result)

	def inst_jump(self):
		self.place += 1
		self.place = self.head - 1

	def inst_jump_if_true(self):
		self.place += 1
		if self.pop():
			self.place = self.head - 1

	def inst_jump_if_false(self):
		self.place += 1
		if not self.pop():
			self.place = self.head - 1

	def inst_store_in_cache(self):
		# print(self.stack)
		value = self.pop()
		cache_key = self.pop()
		function = self.pop()
		function.cache[cache_key] = value
		self.push(value)

	def inst_special_map(self):
		function = self.stack[-3]
		source = self.stack[-2]
		dest = self.stack[-1]
		if not isinstance(function, (Function, BuiltinFunction)):
			raise EvaluationError('map function requires a function as its first arguments')
		if function.macro:
			raise EvaluationError('map function does not support taking a macro function')
		if len(dest) < len(source):
			value = source.items[len(dest)]
			self.call_function(function, [value], self.place + 1)
		else:
			# Cleanup the stack and push the result
			self.pop_n(3)
			self.push(dest)
			# Skip the cache and map store instructions
			self.place += 2

	def inst_special_map_store(self):
		result = self.pop()
		self.top.items.append(result)
		self.place -= 2 + 1

	def inst_special_reduce(self):
		function = self.stack[-4]
		array = self.stack[-3]
		value = self.stack[-2]
		index = self.stack[-1]
		# Assumes datatypes are correct. Might want to add friendly errors later.
		if index < len(array):
			next_item = array.items[index]
			self.call_function(function, [value, next_item], self.place + 1)
		else:
			self.pop()
			self.pop()
			self.pop()
			self.pop()
			self.push(value)
			# Skip the store instruction and the second reduce instruction
			self.place += 2

	def inst_special_reduce_store(self):
		result = self.pop()
		self.stack[-2] = result
		self.stack[-1] += 1
		self.place -= 3

	def call_function(self, function, arguments, return_to):
		assert(self.bytes[return_to] == bytecode.I.STORE_IN_CACHE)
		if isinstance(function, BuiltinFunction) or isinstance(function, Array):
			result = function(*arguments)
			self.push(result)
			self.place = return_to + 1 # Skip the 'store in cache' instruction
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
				self.push(function.cache[cache_key])
				self.place = return_to + 1
			else:
				if function.macro:
					# Return here after the function is done but skip the STORE_IN_CACHE instruction
					self.push(return_to + 1)
				else:
					# Required for storing the result in the result cache
					self.push(function)
					self.push(cache_key)
					# Return here after the function is done
					self.push(return_to)
				# Remember the current scope
				self.push(self.current_scope)
				self.current_scope = new_scope
				self.place = addr + 3 + num_parameters
		else:
			raise EvaluationError('{} is not a function'.format(function))
		self.place -= 1 # Negate the +1 after this


def test(string):
	# print('=========================================')
	# print('   ', string)
	# print('=========================================')
	tokens, ast = parse(string)
	# print(json.dumps(ast, indent = 4))
	# bytes = bytecode.build({'#': 'program', 'items': [ast]})
	builder = bytecode.CodeBuilder()
	bytes = runtime.wrap_with_runtime(builder, ast)
	# for index, byte in enumerate(bytes):
	# 	print('{:3d} - {}'.format(index, byte))
	vm = Interpereter(bytes, builder = builder, trace = True)
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
