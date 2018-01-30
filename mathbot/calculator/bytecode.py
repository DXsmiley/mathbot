import enum
import calculator.parser as parser
import calculator.errors
import calculator.functions
import itertools
import json
import sympy
import inspect


@enum.unique
class I(enum.IntEnum):
	NOTHING = 0
	CONSTANT = 1
	BIN_ADD = 2
	BIN_SUB = 3
	BIN_MUL = 4
	BIN_DIV = 5
	BIN_MOD = 6
	BIN_POW = 7
	BIN_AND = 8
	BIN_OR_ = 9
	BIN_DIE = 10
	UNR_NOT = 11
	UNR_MIN = 12
	UNR_FAC = 13
	JUMP_IF_MACRO = 14
	ARG_LIST_END = 15
	ARG_LIST_END_NO_CACHE = 54
	ARG_LIST_END_WITH_TCO = 65
	WORD = 16
	ASSIGNMENT = 17
	DECLARE_SYMBOL = 59
	STACK_SWAP = 18
	END = 19
	# FUNCTION_MACRO = 20
	FUNCTION_NORMAL = 21
	RETURN = 22
	JUMP = 23
	JUMP_IF_TRUE = 24
	JUMP_IF_FALSE = 25
	DUPLICATE = 26
	DISCARD = 27

	BIN_LESS = 28
	BIN_MORE = 29
	BIN_L_EQ = 30
	BIN_M_EQ = 31
	BIN_EQUL = 33
	BIN_N_EQ = 34

	CMP_LESS = 35
	CMP_MORE = 36
	CMP_L_EQ = 37
	CMP_M_EQ = 38
	CMP_EQUL = 39
	CMP_N_EQ = 40

	STORE_IN_CACHE = 41
	# DEMACROIFY = 42
	# STORE_DEMACROD = 43

	ACCESS_GLOBAL = 44
	ACCESS_LOCAL = 45
	ACCESS_SEMI = 46
	ACCESS_ARRAY_ELEMENT = 53

	CONSTANT_EMPTY_ARRAY = 50

	BEGIN_PROTECTED_GLOBAL_BLOCK = 57
	END_PROTECTED_GLOBAL_BLOCK = 58

	LIST_CREATE_EMPTY = 60
	LIST_EXTRACT_FIRST = 61
	LIST_EXTRACT_REST = 62
	LIST_PREPEND = 63
	LIST_CONCAT = 64

	PUSH_ERROR_STOPGAP = 66

	CONSTANT_STRING = 67
	CONSTANT_GLYPH = 68

	# Next to use: 69


OPERATOR_DICT = {
	'+': I.BIN_ADD,
	'-': I.BIN_SUB,
	'*': I.BIN_MUL,
	'/': I.BIN_DIV,
	'^': I.BIN_POW,
	'%': I.BIN_MOD,
	'&&': I.BIN_AND,
	'||': I.BIN_OR_,
	'<': I.BIN_LESS,
	'>': I.BIN_MORE,
	'<=': I.BIN_L_EQ,
	'>=': I.BIN_M_EQ,
	'==': I.BIN_EQUL,
	'!=': I.BIN_N_EQ,
	':': I.LIST_PREPEND
}


COMPARATOR_DICT = {
	'<': I.CMP_LESS,
	'>': I.CMP_MORE,
	'<=': I.CMP_L_EQ,
	'>=': I.CMP_M_EQ,
	'==': I.CMP_EQUL,
	'!=': I.CMP_N_EQ
}


PROTECTED_NAMES = [
	'if',
	'ifelse',
	'map',
	'filter',
	'reduce',
	'try'
]


class Pointer:

	def __init__(self, destination):
		self.destination = destination


class Destination:

	def __init__(self):
		self.location = None


class Scope:

	def __init__(self, names, superscope = None):
		self.superscope = superscope
		self.name_mapping = {n: i for i, n in enumerate(names)}

	def find_value(self, name, depth = 0):
		if name in self.name_mapping:
			return self, depth, self.name_mapping[name]
		if self.superscope is None:
			self.name_mapping[name] = len(self.name_mapping)
			return self, depth, self.name_mapping[name]
		return self.superscope.find_value(name, depth + 1)


class Keys:

	names = [
		'scope',
		'unsafe',
		'allow_tco'
	]

	def __init__(self, **kwargs):
		self.checknames(kwargs)
		for i in Keys.names:
			if i not in kwargs:
				raise NameError('Property {} not specified for Keys'.format(i))
		self.values = kwargs

	def __call__(self, **kwargs):
		self.checknames(kwargs)
		d = {k:kwargs.get(k, self.values.get(k)) for k in Keys.names}
		return Keys(**d)

	def __getitem__(self, k):
		return self.values[k]

	def checknames(self, dct):
		for i in dct:
			if i not in Keys.names:
				raise NameError('{} is not a valid property for Keys'.format(i))


class ConstructedBytecode:

	def __init__(self, bytecode, error_link):
		self.bytecode = bytecode
		self.error_link = error_link

	def dump(self, release = False):
		''' Produces a representation of the bytecode that should,
			in theory, be transferrable to another computer, or
			be loaded by a different program.
		'''
		result = []
		sources = {}
		for i, e in zip(self.bytecode, self.error_link):
			if i is None:
				result.append(['nul'])
			elif isinstance(i, I):
				result.append([
					'ist',
					int(i),
					'0' if release or e is None else e['position'],
					'?' if release or e is None else e['name']
				])
				if e is not None:
					sources[e['name']] = e['code']
			elif isinstance(i, str):
				result.append(['str', i])
			elif isinstance(i, (int, sympy.Integer)):
				result.append(['int', int(i)])
			elif isinstance(i, (float, sympy.Number)):
				result.append(['flt', i])
			elif isinstance(i, complex):
				result.append(['cpx', i.real, i.imag])
			else:
				raise Exception('Unknown bytecode item: {} ({})'.format(str(i), i.__class__))
		toline = lambda items : ' '.join(map(str, items))
		result = 'bytecode 0 0 0 (unstable)\n' + '\n'.join(map(toline, result)) + '\n'
		if not release:
			for key, value in sources.items():
				result += 'source {} {} {}\n{}\n'.format(key, len(value), value.count('\n'), value)
		return result


class CodeBuilder:

	def __init__(self, offset = 0):
		self.segments = []
		self.segments_backend = []
		self.offset = offset
		self.globalscope = Scope([])
		self.bytecode = []
		self.error_link = []

	def new_segment(self, late = False):
		seg = CodeSegment(self)
		if late:
			self.segments_backend.append(seg)
		else:
			self.segments.append(seg)
		return seg

	def bytecodeify(self, ast, late = False, unsafe = False):
		keys = Keys(unsafe = unsafe, scope = self.globalscope, allow_tco = False)
		self.new_segment().bytecodeify(ast, keys)

	def dump(self):
		newcode = []
		newerrs = []
		for i in itertools.chain(self.segments, self.segments_backend):
			newcode += i.items
			newerrs += i.error_link
		self.segments = []
		self.segments_backend = []
		offset = self.offset + len(self.bytecode)
		# Determine the location of the destinations
		for address, item in enumerate(newcode):
			if isinstance(item, Destination):
				assert item.location is None
				item.location = address + offset
				newcode[address] = I.NOTHING
		# Link the pointers up to their destinations
		for address, item in enumerate(newcode):
			if isinstance(item, Pointer):
				assert newcode[address].destination.location is not None
				newcode[address] = newcode[address].destination.location
		self.bytecode += newcode
		self.error_link += newerrs
		return ConstructedBytecode(self.bytecode[:], self.error_link[:])


class CodeSegment:

	def __init__(self, builder):
		self.builder = builder
		self.start_address = None
		self.items = []
		self.error_link = []

	def new_segment(self, late = False):
		return self.builder.new_segment(late = late)

	def push(self, *items, error = None):
		self.items += items
		self.error_link += [error] * len(items)

	def bytecodeify(self, node, keys):
		# TCO not allowed in most cirumstances. Get the value and then set it. The real value will be passed to the handler function if the function asks for it.
		allow_tco = keys['allow_tco']
		keys = keys(allow_tco = False)
		# Branch by the current node type
		node_type = node['#']
		handler = getattr(self, 'btcfy_' + node_type, None)
		if handler is None:
			raise calculator.errors.CompilationError('Unknown AST node: {}. Cannot convert to bytecode.'.format(node_type))
		h_params, _, _, _ = inspect.getargspec(handler)
		if 'allow_tco' in h_params:
			return handler(node, keys, allow_tco)
		return handler(node, keys)

	def btcfy_number(self, node, _):
		''' Bytecodifies a number node '''
		self.push(I.CONSTANT, convert_number(node['string']))

	def btcfy_glyph(self, node, _):
		''' Bytecodifies a glyph node '''
		string = node['string'][1:]
		if string == '\\;':
			string = '`'
		else:
			string = bytes(string, 'utf-8').decode('unicode_escape')
		self.push(I.CONSTANT_GLYPH, string)

	def btcfy_string(self, node, _):
		''' Bytecodifies a string node '''
		string = node['string'][1:-1]
		string = bytes(string, 'utf-8').decode('unicode_escape')
		self.push(I.CONSTANT_STRING, string)

	def btcfy_bin_op(self, node, keys):
		op = node['operator']
		left = node['left']
		right = node['right']
		er = node['token']['source']
		if op == '&&': # Logical and
			end = Destination()
			self.bytecodeify(left, keys)
			self.push(
				I.DUPLICATE,
				I.JUMP_IF_FALSE,
				Pointer(end),
				error = er
			)
			self.bytecodeify(right, keys)
			self.push(
				I.BIN_AND,
				end,
				error = er
			)
		elif op == '||': # Logical or
			end = Destination()
			self.bytecodeify(left, keys)
			self.push(
				I.DUPLICATE,
				I.JUMP_IF_TRUE,
				Pointer(end),
				error = er
			)
			self.bytecodeify(right, keys)
			self.push(
				I.BIN_OR_,
				end,
				error = er
			)
		else:
			self.bytecodeify(right, keys)
			self.bytecodeify(left, keys)
			self.push(OPERATOR_DICT[op], error = node['token']['source'])

	def btcfy_not(self, node, keys):
		self.bytecodeify(node['expression'], keys)
		self.push(I.UNR_NOT, error = node['token']['source'])

	def btcfy_uminus(self, node, keys):
		self.bytecodeify(node['value'], keys)
		self.push(I.UNR_MIN, error = node['token']['source'])

	def btcfy_word(self, node, keys):
		scope, depth, index = keys['scope'].find_value(node['string'].lower())
		if scope == self.builder.globalscope:
			# NOTE: Only global variables can fail to be found,
			# so we only need the name for this one.
			self.push(I.ACCESS_GLOBAL)
			self.push(index)
			self.push(node['string'], error = node['source'])
		elif depth == 0:
			self.push(I.ACCESS_LOCAL)
			self.push(index)
		else:
			self.push(I.ACCESS_SEMI)
			self.push(depth)
			self.push(index)

	def btcfy_factorial(self, node, keys):
		self.bytecodeify(node['value'], keys)
		self.push(I.UNR_FAC, error = node['token']['source'])

	def btcfy_assignment(self, node, keys):
		name = node['variable']['string'].lower()
		if (node['value']['#'] == 'function_definition'):
			node['value']['name'] = name
		self.bytecodeify(node['value'], keys)
		if name in PROTECTED_NAMES and not keys['unsafe']:
			m = 'Cannot assign to variable "{}"'.format(name)
			raise calculator.errors.CompilationError(m, node['variable'])
		scope, depth, index = keys['scope'].find_value(name)
		assert(scope == self.builder.globalscope)
		# print(scope, depth, index)
		self.push(I.ASSIGNMENT)
		self.push(index)

	def btcfy_declare_symbol(self, node, keys):
		name = node['name']['string'].lower()
		if name in PROTECTED_NAMES and not keys['unsafe']:
			m = 'Cannot assign to variable "{}"'.format(name)
			raise calculator.errors.CompilationError(m, node['name'])
		scope, depth, index = keys['scope'].find_value(name)
		assert(scope == self.builder.globalscope)
		self.push(I.DECLARE_SYMBOL)
		self.push(index)
		self.push(name)

	def btcfy_statement_list(self, node, keys):
		self.bytecodeify(node['statement'], keys)
		if node['next'] is not None:
			self.bytecodeify(node['next'], keys)

	def btcfy_program(self, node, keys):
		for i in node['items']:
			self.bytecodeify(i, keys)

	def btcfy_end(self, node, keys):
		self.push(I.END)

	def btcfy_function_definition(self, node, keys):
		# Create the function itself
		start_pointer = self.define_function(node, keys)
		# Create the bytecode for the current scope
		# self.push(I.FUNCTION_MACRO if node['kind'] == '~>' else I.FUNCTION_NORMAL)
		self.push(I.FUNCTION_NORMAL)
		self.push(start_pointer)

	def btcfy_comparison(self, node, keys):
		if len(node['rest']) == 1:
			# Can get away with a simple binary operator like the others
			self.bytecodeify(node['rest'][0]['value'], keys)
			self.bytecodeify(node['first'], keys)
			op = node['rest'][0]['operator']
			er = node['rest'][0]['token']['source']
			self.push(OPERATOR_DICT[op], error = er)
		else:
			bailed = Destination()
			end = Destination()
			self.push(I.CONSTANT, 1)
			self.bytecodeify(node['first'], keys)
			for index, ast in enumerate(node['rest']):
				if index > 0:
					self.push(
						I.STACK_SWAP, # Get the flag on top
						I.DUPLICATE,  # Copy the flag (copy consumed by branch)
						I.JUMP_IF_FALSE, # If its zero, bail
						Pointer(bailed),
						I.STACK_SWAP # Put the value back on top
					)
				self.bytecodeify(ast['value'], keys)
				self.push(COMPARATOR_DICT[ast['operator']], error = ast['token']['source'])
			self.push(
				I.JUMP,
				Pointer(end),
				bailed,
				I.STACK_SWAP,
				end,
				I.DISCARD,
			)

	def btcfy_period(self, node, keys):
		self.push(I.LIST_CREATE_EMPTY)

	def btcfy_head(self, node, keys):
		self.bytecodeify(node['expression'], keys)
		self.push(I.LIST_EXTRACT_FIRST, error = node['token']['source'])

	def btcfy_tail(self, node, keys):
		self.bytecodeify(node['expression'], keys)
		self.push(I.LIST_EXTRACT_REST, error = node['token']['source'])

	def btcfy_function_call(self, node, keys, allow_tco):
		args = node.get('arguments', {'items': []})['items']
		function_name = node['function']['string'].lower() if node['function']['#'] == 'word' else None
		handler = self.btcfy_function_call_normal
		if function_name:
			handler = getattr(self, 'btcfy_func_' + function_name, handler)
		handler(node, keys, args, allow_tco)

	def btcfy_function_call_normal(self, node, keys, args, allow_tco):
		call_marker_errinfo = node['arguments']['edges']['start']['source']
		# IDEA: If the function contains only a small amount of code, we can also
		# inline it (for normal function calls). Cannot inline everything since
		# this leads to exponential code growth.
		argument_functions = [
			self.define_function({
				'#': 'function_definition',
				'parameters': {'items': []},
				'kind': '->',
				'expression': i
			}, keys) for i in args[::-1]
		]
		self.bytecodeify(node['function'], keys)
		landing_macro = Destination()
		landing_end = Destination()
		# Need to jump because normal functions and macros are handled differently
		self.push(I.JUMP_IF_MACRO)
		self.push(Pointer(landing_macro))
		# Handle if normal function
		for i in argument_functions:
			self.push(I.FUNCTION_NORMAL)
			self.push(i)
			self.push(I.ARG_LIST_END_NO_CACHE)
			self.push(0)
		if allow_tco:
			self.push(I.ARG_LIST_END_WITH_TCO)
		else:
			self.push(I.ARG_LIST_END)
		self.push(len(args), error = call_marker_errinfo)
		self.push(I.JUMP)
		self.push(Pointer(landing_end))
		# Handle if macro function
		self.push(landing_macro)
		for i in argument_functions:
			self.push(I.FUNCTION_NORMAL)
			self.push(i)
		self.push(I.ARG_LIST_END_NO_CACHE, error = call_marker_errinfo)
		self.push(len(args))
		# Aaaaand we done here
		self.push(landing_end)

	def btcfy_func_try(self, node, keys, args, allow_tco):
		if len(args) < 2:
			raise calculator.error.CompilationError('Too few arguments for try function')
		block_end = Destination()
		land_on_error = Destination()
		for case in args[:-1]:
			self.push(I.PUSH_ERROR_STOPGAP, Pointer(land_on_error), 0)
			self.bytecodeify(case, keys)
			self.push(
				I.STACK_SWAP, # Swap the top two items so the stopgap is on top
				I.DISCARD,    # Discard the swapgap
				I.JUMP,       # Jump to the end of the block
				Pointer(block_end),
				land_on_error # This is the start of the next case
			)
			land_on_error = Destination()
		self.bytecodeify(args[-1], keys)
		self.push(block_end)

	def btcfy_func_ifelse(self, node, keys, args, allow_tco):
		if len(args) < 3 or len(args) % 2 == 0:
			raise calculator.errors.CompilationError('Invalid number of arguments for ifelse function')
		p_end = Destination()
		p_false = Destination()
		for condition, result in zip(args[::2], args[1::2]):
			self.bytecodeify(condition, keys)
			self.push(I.JUMP_IF_FALSE)
			self.push(Pointer(p_false))
			self.bytecodeify(result, keys)
			self.push(I.JUMP)
			self.push(Pointer(p_end))
			self.push(p_false)
			p_false = Destination()
		self.bytecodeify(args[-1], keys)
		self.push(p_end)

	def btcfy_func_if(self, node, keys, args, allow_tco):
		if len(args) != 3:
			raise calculator.errors.CompilationError('Invalid number of arguments for if function')
		p_end = Destination()
		p_false = Destination()
		self.bytecodeify(args[0], keys())
		self.push(I.JUMP_IF_FALSE)
		self.push(Pointer(p_false))
		self.bytecodeify(args[1], keys(allow_tco = allow_tco))
		self.push(I.JUMP)
		self.push(Pointer(p_end))
		self.push(p_false)
		self.bytecodeify(args[2], keys(allow_tco = allow_tco))
		self.push(p_end)

	def define_function(self, node, keys):
		contents = self.new_segment(late = True)
		start_address = Destination()
		contents.push(start_address)
		contents.push(node.get('name', '?').lower())
		params = [i['string'].lower() for i in node['parameters']['items']]
		for n, i in zip(params, node['parameters']['items']):
			if n in PROTECTED_NAMES:
				m = '"{}" is not allowed as a funcation parameter'.format(n)
				raise calculator.errors.CompilationError(m, i)
		contents.push(len(params))
		# for i in params:
		# 	contents.push(i)
		contents.push(node.get('variadic', 0))
		is_macro = int(node.get('kind') == '~>')
		contents.push(is_macro)
		if len(params) == 0:
			contents.bytecodeify(node['expression'], keys(allow_tco = True))
		else:
			subscope = Scope(params, superscope = keys['scope'])
			contents.bytecodeify(node['expression'], keys(allow_tco = True, scope = subscope))
		# if not is_macro:
		# 	contents.push(I.STORE_IN_CACHE)
		contents.push(I.STORE_IN_CACHE)
		contents.push(I.RETURN)
		return Pointer(start_address)


def convert_number(x):
	if (x[-1] in 'iI'):
		return sympy.I * sympy.Number(x[:-1])
	return sympy.Number(x)
	# try:
	# 	try:
	# 		return int(x)
	# 	except Exception:
	# 		return float(x)
	# except Exception:
	# 	return complex(x.replace('i', 'j'))


def build(ast, offset = 0):
	builder = CodeBuilder(offset = offset)
	builder.bytecodeify(ast)
	return builder.dump()


def stringify(bytecode):
	result = []
	for i in bytecode:
		if i is None:
			result.append('nothing')
		elif isinstance(i, I):
			result.append('_')
			result.append(int(i))
		elif isinstance(i, str):
			result.append('s')
			result.append(i)
		elif isinstance(i, int):
			result.append('i')
			result.append(int(i))
		elif isinstance(i, float):
			result.append('f')
			result.append(i)
		elif isinstance(i, complex):
			result.append('c')
			result.append(i.real)
			result.append(i.imag)
		else:
			raise Exception('Unknown bytecode item: {} ({})'.format(str(i), i.__type__))
	return ' '.join(map(str, result))
