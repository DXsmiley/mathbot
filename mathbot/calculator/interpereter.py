import inspect
import json
import asyncio
import math
import random
import collections
import numbers
import sys
import sympy
import operator
import warnings
import traceback

import calculator.runtime as runtime
import calculator.bytecode as bytecode
import calculator.errors
from calculator.errors import EvaluationError
from calculator.parser import parse
from calculator.functions import *
import calculator.operators as operators
import calculator.crucible


class ScopeMissedError(Exception):
	pass


DataSlot = collections.namedtuple('DataSlot', 'value security')


class IndexedScope:

	# NOTE: Not really sure why I have both size and values here. 
	def __init__(self, superscope, size, values):
		self.superscope = superscope
		if size != len(values):
			raise calculator.errors.SystemError('Attempted to create a scope with number of values unequal to the size')
		self.slots = [DataSlot(i, 0) for i in values]

	def get(scope, index, depth):
		while depth > 0:
			scope = scope.superscope
			depth -= 1
		if index >= len(scope.slots) or scope.slots[index].value is None:
			raise ScopeMissedError
		return scope.slots[index].value

	def set(scope, index, depth, value, permission = 0, protection = None):
		while depth > 0:
			scope = scope.superscope
			depth -= 1
		while len(scope.slots) <= index:
			scope.slots.append(DataSlot(None, 0))
		_, current_security = scope.slots[index]
		if current_security > permission:
			raise EvaluationError('Not permitted to perform this assignment')
		scope.slots[index] = DataSlot(value, protection if protection is not None else current_security)

	def reset(scope, index, depth, permission = 0, protection = None):
		while depth > 0:
			scope = scope.superscope
			depth -= 1
		if index < len(scope.slots):
			_, current_security = scope.slots[index]
			if current_security > permission:
				raise EvaluationError('Not permitted to perform this unassignment')
			scope.slots[index] = DataSlot(None, protection if protection is not None else current_security)

	def __repr__(self):
		return 'indexed-scope'


async def do_nothing_async():
	pass


async def protected_power(use_crucible, a, b):
	if use_crucible:
		try:
			return await calculator.crucible.run(_protected_power_crucible, (a, b), timeout=2)
		except asyncio.TimeoutError:
			raise EvaluationError('Operation timed out. Perhaps the values were too large?')
	else:
		return _protected_power_crucible(a, b)


# Top level function to prevent copying of scope
def _protected_power_crucible(a, b):
	result = a ** b
	# ensure that the result isn't going to expode on the main program
	# if str(result) explodes, this process will time out
	str(result)
	return result


class FunctionInspector:
	''' Used to provide an abstraction around accessing information about a function,
		as opposed to looking at the bytecode directly.

		Function data is stored as follows:
			- (null) <- function_object.address
			- num_arguments
			- is_variadic <- either 0 or 1
			- is_macro <- either 0 or 1
			- (code starts here)
	'''

	def __init__(self, interpereter, function_object):
		assert isinstance(function_object, Function)
		# This is all we need from the interpereter, so grab it
		# if we need more information later we can take it
		self.bytes = function_object.segment.bytecode
		self.function_object = function_object
		self.address = self.function_object.address

	@property
	def name(self):
		return self.bytes[self.address + 1]

	@property
	def num_parameters(self):
		return self.bytes[self.address + 2]

	@property
	def is_variadic(self):
		return self.bytes[self.address + 3]

	@property
	def is_macro(self):
		return self.bytes[self.address + 4]

	@property
	def code_address(self):
		return self.address + 5

	@property
	def code_segment(self):
		return self.function_object.segment


class CallingCache:

	def __init__(self, capacity=10000):
		self.clear()
		self.capacity = 10000

	def __contains__(self, key):
		return key in self.values

	def __setitem__(self, key, value):
		assert key not in self.values
		self.values[key] = value
		self.queue.append(key)
		if len(self.queue) > self.capacity:
			drop = self.queue.popleft()
			del self.values[drop]

	def __getitem__(self, key):
		return self.values[key]

	def clear(self):
		self.values = {}
		self.queue = collections.deque()


class ErrorStopGap:

	__slots__ = ['handler_segment', 'handler_address', 'should_pass']

	def __init__(self, segment, address, should_pass):
		self.handler_segment = segment
		self.handler_address = address
		self.should_pass = should_pass


class Interpereter:

	def __init__(self, *, trace=False, yield_rate=100, use_crucible=False):
		self.use_crucible = use_crucible
		self.calling_cache = CallingCache()
		self.trace = trace
		self.bytes = None
		self.place = 0
		self.stack = [None]
		self.yield_rate = yield_rate
		self.root_scope = IndexedScope(None, 0, [])
		self.current_scope = self.root_scope
		self.protected_assignment_mode = False
		self.assignment_protection_level = None
		self.assignment_auth_level = 0
		self.enable_exception_handler = True
		b = bytecode.I # pylint: no-invalid-name
		self.switch_dictionary = {
			b.NOTHING: do_nothing_async,
			b.CONSTANT: self.inst_constant,
			b.BIN_ADD: self.inst_add,
			b.BIN_SUB: self.inst_sub,
			b.BIN_MUL: self.inst_mul,
			b.BIN_DIV: self.inst_div,
			b.BIN_MOD: self.inst_mod,
			b.BIN_POW: self.inst_pow,
			# b.BIN_DIE: self.inst_bin_die,
			b.BIN_AND: self.inst_and,
			b.BIN_OR_: self.inst_or,
			b.JUMP_IF_MACRO: self.inst_jump_if_macro,
			# b.DEMACROIFY: self.inst_demacroify,
			# b.STORE_DEMACROD: self.inst_store_demacrod,
			b.ARG_LIST_END: self.inst_arg_list_end,
			b.ARG_LIST_END_NO_CACHE: self.inst_arg_list_end_no_cache,
			b.ARG_LIST_END_WITH_TCO: self.inst_arg_list_end_with_tco,
			b.ASSIGNMENT: self.inst_assignment,
			b.DECLARE_SYMBOL: self.inst_declare_symbol,
			b.WORD: self.inst_word,
			b.ACCESS_LOCAL: self.inst_access_local,
			b.ACCESS_GLOBAL: self.inst_access_gobal,
			b.ACCESS_SEMI: self.inst_access_semi,
			b.ACCESS_ARRAY_ELEMENT: self.inst_access_array_element,
			b.UNLOAD: self.inst_unload,
			b.FUNCTION_NORMAL: self.inst_function,
			# b.FUNCTION_NORMAL: self.inst_function_normal,
			# b.FUNCTION_MACRO: self.inst_function_macro,
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
			b.CONSTANT_EMPTY_ARRAY: self.inst_constant_empty_array,
			b.DUPLICATE: self.inst_duplicate,
			b.STACK_SWAP: self.inst_stack_swap,
			b.BEGIN_PROTECTED_GLOBAL_BLOCK: self.inst_protected_mode_enable,
			b.END_PROTECTED_GLOBAL_BLOCK: self.inst_protected_mode_disable,
			b.LIST_CREATE_EMPTY: self.inst_list_create_empty,
			b.LIST_EXTRACT_FIRST: self.inst_list_extract_first,
			b.LIST_EXTRACT_REST: self.inst_list_extract_rest,
			b.LIST_PREPEND: self.inst_list_prepend,
			b.PUSH_ERROR_STOPGAP: self.inst_push_error_stopgap,
			b.CONSTANT_STRING: self.inst_constant_string,
			b.CONSTANT_GLYPH: self.inst_constant_glyph
		}

	# def swap_bytecode(self, constructed_bytecode):
	# 	self.bytes = code_constructed.bytecode
	# 	self.erlnk = code_constructed.error_link

	def clear_cache(self):
		''' Clears the function call cache '''
		self.calling_cache.clear()

	# def state_freeze(self):
	# 	''' Returns the state of the interpereter so that it may be recovered later.
	# 		Global variables are not considered 'frozen'
	# 	'''
	# 	return FrozenState(self)

	# def state_thaw(self, frozen):
	# 	''' Returns to a frozen state '''
	# 	self.place = frozen.place
	# 	self.stack = frozen.stack[:]
	# 	self.current_scope = frozen.current_scope

	@property
	def erlnk(self):
		return self.bytes.error_link

	@property
	def head(self):
		'''Return the instruction under the playhead'''
		return self.bytes[self.place]

	def next(self):
		''' Advance the playhead and result the new instruction '''
		self.place += 1
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
		return [self.stack.pop() for _ in range(count)]

	def push(self, item):
		'''Push an item to the stop of the stack'''
		self.stack.append(item)

	def run(self, **kwargs):
		loop = asyncio.get_event_loop()
		return loop.run_until_complete(self.run_async(**kwargs))

	async def run_async(self, segment=None, tick_limit=None, error_if_exhausted=False,
			get_entire_stack=False, assignment_protection_level=None, assignment_auth_level=0):
		''' Run some number of ticks.
			tick_limit         - The maximum number of ticks to run. If not specified there is no limit.
			error_if_exhausted - If True, an error will be thrown if execution is not finished in the
								 specified number of ticks.
			expect_complete    - Deprecated
		'''
		self.assignment_protection_level = assignment_protection_level
		self.assignment_auth_level = assignment_auth_level
		self.bytes = segment
		self.place = 0
		if tick_limit is None:
			while self.head != bytecode.I.END:
				await self.tick()
		else:
			while self.head != bytecode.I.END and tick_limit > 0:
				tick_limit -= 1
				await self.tick()
		if error_if_exhausted and tick_limit == 0:
			raise EvaluationError('Execution timed out (by tick count)')
		if get_entire_stack:
			return self.stack[1:]
		return self.top

	async def tick(self):
		''' Run a single tick '''
		if self.trace:
			print(self.place, self.head, self.stack)
		inst = self.switch_dictionary.get(self.head)
		if not isinstance(self.head, bytecode.I) or inst is None:
			raise SystemError('Tried to run unknown instruction: ' + repr(self.head))
		if self.enable_exception_handler:
			try:
				await inst()
			except EvaluationError as error:
				error._linking = self.erlnk[self.place]
				if self.panic(error):
					raise error
		else:
			await inst()
		# Let the event loop do some work.
		await asyncio.sleep(0)
		self.place += 1

	def panic(self, error):
		try:
			while not isinstance(self.top, ErrorStopGap):
				# No stopgap found, raise the error instead
				self.pop()
		except IndexError:
			return True
		stopgap = self.pop()
		self.bytes = stopgap.handler_segment
		self.place = stopgap.handler_address - 1
		return False

	async def inst_constant(self):
		''' Push a constant to the stack '''
		self.place += 1
		self.push(self.head)

	async def inst_constant_empty_array(self):
		''' Push an empty array to the stack '''
		warnings.warn('Instruction CONSTANT_EMPTY_ARRAY is deprecated', DeprecationWarning)
		self.push(Array([]))

	async def inst_constant_string(self):
		''' Push a string to the stack '''
		string = self.next()
		self.push(create_list(map(Glyph, string)))

	async def inst_constant_glyph(self):
		''' Push a glyph to the stack '''
		c = self.next()
		self.push(Glyph(c))

	async def inst_duplicate(self):
		''' Duplicate the top item of the stack '''
		self.push(self.top)

	async def inst_stack_swap(self):
		''' Swap the top two items of the stack '''
		a = self.pop()
		b = self.pop()
		self.push(a)
		self.push(b)

	async def inst_protected_mode_enable(self):
		''' Specify that any assignments from now on should be protected '''
		warnings.warn('Instruction BEGIN_PROTECTED_GLOBAL_BLOCK is deprecated', DeprecationWarning)
		self.protected_assignment_mode = True

	async def inst_protected_mode_disable(self):
		''' Specify that any assignments from now on should not be protected '''
		warnings.warn('Instruction END_PROTECTED_GLOBAL_BLOCK is deprecated', DeprecationWarning)
		self.protected_assignment_mode = False

	def make_bin_op_instruction(op, is_coroutine=False):
		''' Create a handler for a binary operator instruction '''
		async def internal(self):
			left = self.pop()
			right = self.pop()
			try:
				result = op(left, right)
				if is_coroutine:
					result = await result
				self.push(result)
			except EvaluationError:
				raise
			except Exception:
				raise EvaluationError('Operation failed on {} and {}', left, right)
		return internal

	inst_add = make_bin_op_instruction(operator.add)
	inst_mul = make_bin_op_instruction(operator.mul)
	inst_sub = make_bin_op_instruction(operator.sub)
	inst_div = make_bin_op_instruction(operator.truediv)
	inst_mod = make_bin_op_instruction(operator.mod)
	# inst_pow = make_bin_op_instruction(protected_power, is_coroutine=True)
	inst_bin_less = make_bin_op_instruction(operators.super_less_than, is_coroutine=True)
	inst_bin_more = make_bin_op_instruction(operators.super_more_than, is_coroutine=True)
	inst_bin_l_eq = make_bin_op_instruction(operators.super_less_eq, is_coroutine=True)
	inst_bin_m_eq = make_bin_op_instruction(operators.super_more_eq, is_coroutine=True)
	inst_bin_equl = make_bin_op_instruction(operators.super_equals, is_coroutine=True)
	inst_bin_n_eq = make_bin_op_instruction(operators.super_not_equals, is_coroutine=True)
	# inst_bin_die = make_bin_op_instruction(rolldie)
	inst_and = make_bin_op_instruction(lambda a, b: (bool(a) and bool(b)))
	inst_or = make_bin_op_instruction(lambda a, b: (bool(a) or bool(b)))

	async def inst_pow(self):
		def _internal(a, b):
			return protected_power(self.use_crucible, a, b)
		await Interpereter.make_bin_op_instruction(_internal, is_coroutine=True)(self)

	async def inst_unr_min(self):
		self.push(-self.pop())

	async def inst_unr_fac(self):
		''' Factorial operator '''
		try:
			original_value = self.pop()
			argument = original_value
			# Prevent a burning attack from happening
			if argument < -2000 or argument > 2000:
				argument = sympy.Number(float(argument))
			result = sympy.factorial(argument)
			if result == sympy.zoo or result == sympy.oo:
				raise TypeError
		except Exception:
			raise EvaluationError('Cannot run factorial function on {}', original_value)
		self.push(result)
		# self.push(operators.function_factorial(self.pop()))

	async def inst_unr_not(self):
		''' Unary not operator '''
		self.push(int(not bool(self.pop())))

	def make_comparison_instruction(comparator):
		''' Create a handler for a binary comparison instruction '''
		async def internal(self):
			right = self.pop()
			left = self.pop()
			try:
				result = bool(await comparator(left, right))
			except EvaluationError:
				raise
			except Exception:
				raise EvaluationError('Operation failed on {} and {}', left, right)
			self.stack[-1] = self.stack[-1] and result
			self.push(right)
		return internal

	inst_cmp_less = make_comparison_instruction(operators.super_less_than)
	inst_cmp_more = make_comparison_instruction(operators.super_more_than)
	inst_cmp_l_eq = make_comparison_instruction(operators.super_less_eq)
	inst_cmp_m_eq = make_comparison_instruction(operators.super_more_eq)
	inst_cmp_equl = make_comparison_instruction(operators.super_equals)
	inst_cmp_n_eq = make_comparison_instruction(operators.super_not_equals)

	async def inst_discard(self):
		''' Discard the top item of the stack '''
		self.pop()

	async def inst_jump_if_macro(self):
		''' Jumps to a place specified by the next instruction IFF the thing on the
			top of the stack is both a function and a macro.
		'''
		self.place += 1
		if isinstance(self.top, Function) and FunctionInspector(self, self.top).is_macro:
			self.perform_jump()

	async def inst_arg_list_end(self, disable_cache = False, do_tco = False):
		''' Specify the end of an argument list.
			Pop the arguments off the stack and call the function.
		'''
		# Look at the number of arguments
		self.place += 1
		stack_arg_count = self.head
		arguments = []
		for i in range(stack_arg_count):
			arg = self.pop()
			if isinstance(arg, Expanded):
				for i in arg:
					arguments.append(i)
			else:
				arguments.append(arg)
		function = self.pop()
		await self.call_function(
			function,
			arguments,
			(self.bytes, self.place + 1),
			disable_cache=disable_cache,
			do_tco=do_tco
		)

	async def inst_arg_list_end_no_cache(self):
		''' Specify the end of an argument list, but explicitly disable the cache. '''
		await self.inst_arg_list_end(disable_cache = True)

	async def inst_arg_list_end_with_tco(self):
		''' Specify the end of an argument list, but specify that tail call optimation can be employed.
			An implementation of the interpereter _should_ be able to treat this as a normal ARG_LIST_END
			with no penalty.
		'''
		await self.inst_arg_list_end(do_tco = True)

	async def inst_word(self):
		''' This is very deprecated '''
		assert(False)
		self.place += 1
		self.push(self.current_scope[self.head])

	async def inst_access_gobal(self):
		''' Retreive a global variable and push it to the top of the stack '''
		index = self.next()
		name = self.next()
		try:
			value = self.root_scope.get(index, 0)
			self.push(value)
		except ScopeMissedError:
			raise calculator.errors.AccessFailedError(name)

	async def inst_access_local(self):
		''' Access a local variable '''
		self.place += 1
		self.push(self.current_scope.get(self.head, 0))

	async def inst_access_semi(self):
		''' Access a variable from a scope above this one '''
		depth = self.next()
		index = self.next()
		self.push(
			self.current_scope.get(
				index,
				depth
			)
		)

	async def inst_access_array_element(self):
		index = self.pop()
		array = self.pop()
		if not isinstance(array, (Array, Interval)):
			raise EvaluationError('Cannot access element of non-array object')
		if not isinstance(index, int):
			raise EvaluationError('Cannot access non-integer element of an array')
		if index < 0 or index >= len(array):
			raise EvaluationError('Attempted to access out-of-bounds element of an array')
		self.push(array(index))

	async def inst_unload(self):
		index = self.next()
		self.root_scope.reset(index, 0)

	async def inst_assignment(self):
		value = self.pop()
		index = self.next()
		self.root_scope.set(index, 0, value,
			permission=self.assignment_auth_level, protection=self.assignment_protection_level)

	async def inst_declare_symbol(self):
		self.place += 1
		index = self.head
		self.place += 1
		name = self.head
		value = sympy.symbols(name)
		self.root_scope.set(index, 0, value)

	async def inst_function(self):
		self.place += 1
		segment, address = self.head
		# print(id(self.bytes), id(segment), address)
		function = Function(segment, address, self.current_scope, '?')
		inspector = FunctionInspector(self, function)
		function.name = inspector.name
		self.push(function)

	# async def inst_function_normal(self):
	# 	self.place += 1
	# 	self.push(Function(self.head, self.current_scope, False))

	# async def inst_function_macro(self):
	# 	self.place += 1
	# 	self.push(Function(self.head, self.current_scope, True))

	async def inst_return(self):
		result = self.pop()
		self.current_scope = self.pop()
		self.bytes, self.place = self.pop()
		self.place -= 1
		self.push(result)

	def perform_jump(self, allow_leap=False):
		''' Jumps to the destination that is sitting under the head.
			If allow_leap is False, landing in a different segment
			to the one you started is forbidden.
		'''
		segment, index = self.head
		# assert allow_leap or segment is self.bytes
		self.bytes = segment
		self.place = index - 1

	async def inst_jump(self):
		self.place += 1
		self.perform_jump()

	async def inst_jump_if_true(self):
		self.place += 1
		if self.pop():
			self.perform_jump()

	async def inst_jump_if_false(self):
		self.place += 1
		if not self.pop():
			self.perform_jump()

	async def inst_store_in_cache(self):
		# print(self.stack)
		value = self.pop()
		cache_key = self.pop()
		if cache_key is not None:
			self.calling_cache[cache_key] = value
		self.push(value)

	async def inst_special_reduce_store(self):
		result = self.pop()
		self.stack[-2] = result
		self.stack[-1] += 1
		self.place -= 1 + 1

	async def inst_list_create_empty(self):
		self.push(calculator.functions.EmptyList())

	async def inst_list_extract_first(self):
		value = self.pop()
		if not isinstance(value, (calculator.functions.ListBase, calculator.functions.Array)):
			raise EvaluationError('Attempted to extract head of non-list')
		self.push(value.head)

	async def inst_list_extract_rest(self):
		value = self.pop()
		if not isinstance(value, (calculator.functions.ListBase, calculator.functions.Array)):
			raise EvaluationError('Attempted to extract tail of non-list')
		self.push(value.rest)

	async def inst_list_prepend(self):
		new = self.pop()
		lst = self.pop()
		if not isinstance(lst, calculator.functions.ListBase):
			raise EvaluationError('Attempt to prepend to start of non-list')
		self.push(calculator.functions.List(new, lst))

	async def inst_push_error_stopgap(self):
		handler_segment, handler_address = self.next()
		should_pass = self.next()
		self.push(ErrorStopGap(handler_segment, handler_address, should_pass))

	async def call_builtin_function(self, function, arguments, return_to):
		try:
			if isinstance(function, BuiltinFunction) and function.is_coroutine:
				result = await function(*arguments)
			else:
				result = function(*arguments)
		except Exception:
			# arg = arguments if len(arguments)
			# pylint: disable=raising-format-tuple
			if not arguments:
				raise EvaluationError('Failed to call {} with no arguments.', function)
			elif len(arguments) == 1:
				raise EvaluationError('Failed to call {} on {}', function, arguments[0])
			else:
				raise EvaluationError('Failed to call {} on {}', function, arguments)
		except EvaluationError:
			raise
		self.push(result)
		self.bytes, self.place = return_to

	async def call_function(self, function, arguments, return_to, disable_cache=False, macro_unprepped=False, do_tco=False):
		if isinstance(function, (BuiltinFunction, Array, Interval, SingularValue)):
			await self.call_builtin_function(function, arguments, return_to)
		elif isinstance(function, Function):
			inspector = FunctionInspector(self, function)
			need_to_call = True
			if not disable_cache:
				cache_key = tuple([function] + arguments)
				if not inspector.is_macro and cache_key in self.calling_cache:
					self.push(self.calling_cache[cache_key])
					self.bytes, self.place = return_to
					need_to_call = False
			if need_to_call:
				num_parameters = inspector.num_parameters
				if inspector.is_variadic:
					if len(arguments) < num_parameters - 1:
						raise EvaluationError('Not enough arguments for variadic function {}', function)
					main = arguments[:num_parameters - 1]
					extra = arguments[num_parameters - 1:]
					scope_array = main
					scope_array.append(Array(extra))
					new_scope = IndexedScope(function.scope, num_parameters, scope_array)
				else:
					if num_parameters != len(arguments):
						raise EvaluationError('Improper number of arguments for function {}', function)
					if num_parameters == 0:
						new_scope = function.scope
					elif inspector.is_macro and macro_unprepped:
						wrapped = tuple(map(SingularValue, arguments))
						new_scope = IndexedScope(function.scope, num_parameters, wrapped)
					else:
						new_scope = IndexedScope(function.scope, num_parameters, arguments)
				# Remember the current scope
				if not do_tco:
					self.push(return_to)
					self.push(self.current_scope)
					# For normal functions, the last thing that happens is that the result is
					# stored in a cache. Need the key in order to do that.
					self.push(None if disable_cache or inspector.is_macro else cache_key)
				# Enter the function
				self.current_scope = new_scope
				self.bytes = inspector.code_segment
				self.place = inspector.code_address
		else:
			raise EvaluationError('{} is not a function', function)
		self.place -= 1 # Negate the +1 after this

	def get_memory_usage(self):
		return deep_getsizeof(self)


class FrozenState:

	__slots__ = ['place', 'stack', 'current_scope']

	def __init__(self, interpereter: Interpereter):
		self.place = interpereter.place
		self.stack = interpereter.stack[:]
		self.current_scope = interpereter.current_scope


def test(string):
	# print('=========================================')
	# print('   ', string)
	# print('=========================================')
	tokens, ast = parse(string)
	# print(json.dumps(ast, indent = 4))
	# bytes = bytecode.build({'#': 'program', 'items': [ast]})
	builder = bytecode.CodeBuilder()
	interpreter_bytes = runtime.wrap_with_runtime(builder, ast)
	# for index, byte in enumerate(bytes):
	# 	print('{:3d} - {}'.format(index, byte))
	vm = Interpereter(interpreter_bytes, builder = builder, trace = True)
	return vm.run(tick_limit = 10000, error_if_exhausted = True)


# def deep_getsizeof(root):
# 	"""Recursively iterate to sum size of object & members."""
# 	seen = set()
# 	def inner(obj):
# 		if id(obj) in seen:
# 			return 0
# 		seen.add(id(obj))
# 		size = sys.getsizeof(obj)
# 		if isinstance(obj, (str, bytes, numbers.Number, range, bytearray)):
# 			pass
# 		elif isinstance(obj, (tuple, list, set, collections.Set, collections.deque)):
# 			size += sum(inner(i) for i in obj)
# 		elif isinstance(obj, collections.Mapping):
# 			size += sum(inner(k) + inner(obj[k]) for k in obj)
# 		# Check for custom object instances - may subclass above too
# 		if hasattr(obj, '__dict__'):
# 			size += inner(vars(obj))
# 		if hasattr(obj, '__slots__'): # can have __slots__ with __dict__
# 			size += sum(inner(getattr(obj, s)) for s in obj.__slots__ if hasattr(obj, s))
# 		return size
# 	return inner(root)


def deep_getsizeof(obj, seen = None):
	"""Recursively finds size of objects in bytes"""
	size = sys.getsizeof(obj)
	seen = seen or set()
	if id(obj) in seen:
		return 0
	seen.add(id(obj))
	if hasattr(obj, '__dict__'):
		for cls in obj.__class__.__mro__:
			if '__dict__' in cls.__dict__:
				d = cls.__dict__['__dict__']
				if inspect.isgetsetdescriptor(d) or inspect.ismemberdescriptor(d):
					size += deep_getsizeof(obj.__dict__, seen)
				break
	if isinstance(obj, dict):
		size += sum((deep_getsizeof(v, seen) for v in obj.values()))
		size += sum((deep_getsizeof(k, seen) for k in obj.keys()))
	elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
		size += sum((deep_getsizeof(i, seen) for i in obj))
	return size
