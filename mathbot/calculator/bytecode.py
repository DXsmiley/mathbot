import enum
import calculator.parser as parser
import calculator.errors
import calculator.functions
import calculator.formatter
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
	UNLOAD = 69

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

	# Next to use: 70


OPERATOR_DICT = {
	'+': I.BIN_ADD,
	'-': I.BIN_SUB,
	'*': I.BIN_MUL,
	'/': I.BIN_DIV,
	'^': I.BIN_POW,
	'~mod': I.BIN_MOD,
	'&&': I.BIN_AND,
	'||': I.BIN_OR_,
	'<': I.BIN_LESS,
	'>': I.BIN_MORE,
	'<=': I.BIN_L_EQ,
	'≤': I.BIN_L_EQ,
	'≯': I.BIN_L_EQ,
	'>=': I.BIN_M_EQ,
	'≥': I.BIN_M_EQ,
	'≮': I.BIN_M_EQ,
	'==': I.BIN_EQUL,
	'!=': I.BIN_N_EQ,
	'≠': I.BIN_N_EQ,
	':': I.LIST_PREPEND
}


COMPARATOR_DICT = {
	'<': I.CMP_LESS,
	'>': I.CMP_MORE,
	'<=': I.CMP_L_EQ,
	'≤': I.CMP_L_EQ,
	'≯': I.CMP_L_EQ,
	'>=': I.CMP_M_EQ,
	'≥': I.CMP_M_EQ,
	'≮': I.CMP_M_EQ,
	'==': I.CMP_EQUL,
	'!=': I.CMP_N_EQ,
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
		self.segment = None
		self.index = None


class GlobalToken:

	__slots__ = ['name']

	def __init__(self, name):
		self.name = name


class Scope:

	__slots__ = ['superscope', 'name_mapping']

	def __init__(self, names, superscope = None):
		self.superscope = superscope
		self.name_mapping = {n: i for i, n in enumerate(names)}

	def find_value(self, name, depth = 0):
		if name in self.name_mapping:
			return self, depth, self.name_mapping[name]
		if self.superscope is None:
			# self.name_mapping[name] = len(self.name_mapping)
			self.name_mapping[name] = GlobalToken(name)
			return self, depth, self.name_mapping[name]
		return self.superscope.find_value(name, depth + 1)


class ConstructionContext:

	def __init__(self, *, scope, unsafe, allow_tco):
		self._staged = False
		self.scope = scope
		self.unsafe = unsafe
		self.allow_tco = allow_tco

	def readyup(self):
		if self._staged:
			raise calculator.errors.CompilationError('Attmped to re-use a ConstructionContext.')
		self._staged = True

	def __call__(self,  **kwargs):
		return ConstructionContext(
			scope=kwargs.get('scope', self.scope),
			unsafe=kwargs.get('unsafe', self.unsafe),
			allow_tco=kwargs.get('allow_tco', False)
		)


class ConstructedBytecode:

	def __init__(self, segment):
		self.bytecode = segment.bytecode
		self.error_link = segment.error_link

	def __getitem__(self, index):
		return self.bytecode[index]

	def __len__(self):
		return len(self.bytecode)

	def __repr__(self):
		return f'Bytecode @{id(self.bytecode)}'

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


class Builder:

	''' Used to convert multiple ASTs into bytecode so that they
		share a given scope.
	'''

	def __init__(self):
		self.globalscope = Scope([])
		self.extrascope = {}

	def build(self, *asts, unsafe=False):
		segment = CodeSegment(self)
		for i in asts:
			segment.add_ast(i, unsafe=unsafe)
		segment.resolve_jump_addresses()
		segment.push(I.END)
		return ConstructedBytecode(segment)

	def resolve_name(self, name):
		if name not in self.extrascope:
			self.extrascope[name] = len(self.extrascope)
		return self.extrascope[name]


class CodeSegment:

	def __init__(self, master):
		self.bytecode = []
		self.error_link = []
		self.master = master


	def add_ast(self, ast, unsafe=False):
		self.bytecodeify(
			ast,
			ConstructionContext(
				scope=self.master.globalscope,
				allow_tco=False,
				unsafe=unsafe
			)
		)

	def resolve_jump_addresses(self):
		for i, v in enumerate(self.bytecode):
			if isinstance(v, Destination):
				v.index = i
				v.segment = self
		for i, v in enumerate(self.bytecode):
			if isinstance(v, GlobalToken):
				self.bytecode[i] = self.master.resolve_name(v.name)
			if isinstance(v, Pointer):
				self.bytecode[i] = (
					ConstructedBytecode(v.destination.segment),
					v.destination.index
				)
			if isinstance(v, Destination):
				self.bytecode[i] = I.NOTHING

	def push(self, *bytecode, error = None):
		self.bytecode += bytecode
		self.error_link += [error] * len(bytecode)

	def bytecodeify(self, node, keys):
		keys.readyup()
		# Branch by the current node type
		node_type = node['#']
		handler = getattr(self, 'btcfy_' + node_type, None)
		if handler is None:
			raise calculator.errors.CompilationError('Unknown AST node: {}. Cannot convert to bytecode.'.format(node_type))
		return handler(node, keys)

	def btcfy_number(self, node, _):
		''' Bytecodifies a number node '''
		self.push(I.CONSTANT, convert_number(node['string']))

	def btcfy_glyph(self, node, _):
		''' Bytecodifies a glyph node '''
		string = node['string'][1:]
		# string = bytes(string, 'utf-8').decode('unicode_escape')
		# print(string, calculator.formatter.string_backslash_escaping(string))
		self.push(I.CONSTANT_GLYPH, calculator.formatter.string_backslash_escaping(string))

	def btcfy_string(self, node, _):
		''' Bytecodifies a string node '''
		string = node['string'][1:-1]
		# string = bytes(string, 'utf-8').decode('unicode_escape')
		# print(string)
		self.push(I.CONSTANT_STRING, calculator.formatter.string_backslash_escaping(string))

	def btcfy_bin_op(self, node, keys):
		op = node['operator']
		left = node['left']
		right = node['right']
		er = node['token']['source']
		if op == '&&': # Logical and
			end = Destination()
			self.bytecodeify(left, keys())
			self.push(
				I.DUPLICATE,
				I.JUMP_IF_FALSE,
				Pointer(end),
				error = er
			)
			self.bytecodeify(right, keys())
			self.push(
				I.BIN_AND,
				end,
				error = er
			)
		elif op == '||': # Logical or
			end = Destination()
			self.bytecodeify(left, keys())
			self.push(
				I.DUPLICATE,
				I.JUMP_IF_TRUE,
				Pointer(end),
				error = er
			)
			self.bytecodeify(right, keys())
			self.push(
				I.BIN_OR_,
				end,
				error = er
			)
		else:
			self.bytecodeify(right, keys())
			self.bytecodeify(left, keys())
			self.push(OPERATOR_DICT[op], error = node['token']['source'])

	def btcfy_not(self, node, keys):
		self.bytecodeify(node['expression'], keys())
		self.push(I.UNR_NOT, error = node['token']['source'])

	def btcfy_uminus(self, node, keys):
		self.bytecodeify(node['value'], keys())
		self.push(I.UNR_MIN, error = node['token']['source'])

	def btcfy_percent_op(self, node, keys):
		self.bytecodeify({'#': 'number', 'string': '100'}, keys())
		self.bytecodeify(node['value'], keys())
		self.push(I.BIN_DIV, error = node['token']['source'])

	def btcfy_word(self, node, keys):
		scope, depth, index = keys.scope.find_value(node['string'].lower())
		if scope == self.master.globalscope:
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

	def btcfy__exact_item_hack(self, node, keys):
		self.push(I.CONSTANT, node['value'])

	def btcfy_factorial(self, node, keys):
		self.bytecodeify(node['value'], keys())
		self.push(I.UNR_FAC, error = node['token']['source'])

	def btcfy_assignment(self, node, keys):
		name = node['variable']['string'].lower()
		# NOTE: If not sure what these two lines are for
		if (node['value']['#'] == 'function_definition'):
			node['value']['name'] = name
		self.bytecodeify(node['value'], keys())
		if name in PROTECTED_NAMES and not keys.unsafe:
			m = 'Cannot assign to variable "{}"'.format(name)
			raise calculator.errors.CompilationError(m, node['variable'])
		scope, depth, index = keys.scope.find_value(name)
		assert scope == self.master.globalscope
		# print(scope, depth, index)
		self.push(I.ASSIGNMENT, index, error=node['variable'].get('source'))

	def btcfy_unload_global(self, node, keys):
		name = node['variable']['string'].lower()
		scope, depth, index = keys.scope.find_value(name)
		self.push(I.UNLOAD, index, error=node['variable'].get('source'))

	def btcfy_declare_symbol(self, node, keys):
		name = node['name']['string'].lower()
		if name in PROTECTED_NAMES and not keys.unsafe:
			m = 'Cannot assign to variable "{}"'.format(name)
			raise calculator.errors.CompilationError(m, node['name'])
		scope, depth, index = keys.scope.find_value(name)
		assert scope == self.master.globalscope
		self.push(I.DECLARE_SYMBOL)
		self.push(index)
		self.push(name)

	def btcfy_program(self, node, keys):
		for i in node['items']:
			self.bytecodeify(i, keys())

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
			self.bytecodeify(node['rest'][0]['value'], keys())
			self.bytecodeify(node['first'], keys())
			op = node['rest'][0]['operator']
			er = node['rest'][0]['token']['source']
			self.push(OPERATOR_DICT[op], error = er)
		else:
			bailed = Destination()
			end = Destination()
			self.push(I.CONSTANT, 1)
			self.bytecodeify(node['first'], keys())
			for index, ast in enumerate(node['rest']):
				if index > 0:
					self.push(
						I.STACK_SWAP, # Get the flag on top
						I.DUPLICATE,  # Copy the flag (copy consumed by branch)
						I.JUMP_IF_FALSE, # If its zero, bail
						Pointer(bailed),
						I.STACK_SWAP # Put the value back on top
					)
				self.bytecodeify(ast['value'], keys())
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
		self.bytecodeify(node['expression'], keys())
		self.push(I.LIST_EXTRACT_FIRST, error = node['token']['source'])

	def btcfy_tail(self, node, keys):
		self.bytecodeify(node['expression'], keys())
		self.push(I.LIST_EXTRACT_REST, error = node['token']['source'])

	def btcfy_list_literal(self, node, keys):
		self.push(I.LIST_CREATE_EMPTY)
		for item in node['items'][::-1]:
			self.bytecodeify(item, keys())
			self.push(I.LIST_PREPEND)

	def btcfy_function_call(self, node, keys):
		args = node.get('arguments', {'items': []})['items']
		function_name = node['function']['string'].lower() if node['function']['#'] == 'word' else None
		handler = self.btcfy_function_call_normal
		if function_name:
			handler = getattr(self, 'btcfy_func_' + function_name, handler)
		handler(node, keys, args)

	def btcfy_function_call_normal(self, node, keys, args):
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
		self.bytecodeify(node['function'], keys())
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
		if keys.allow_tco:
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

	def btcfy_func_try(self, node, keys, args):
		if len(args) < 2:
			raise calculator.error.CompilationError('Too few arguments for try function')
		block_end = Destination()
		land_on_error = Destination()
		for case in args[:-1]:
			self.push(I.PUSH_ERROR_STOPGAP, Pointer(land_on_error), 0)
			self.bytecodeify(case, keys())
			self.push(
				I.STACK_SWAP, # Swap the top two items so the stopgap is on top
				I.DISCARD,    # Discard the swapgap
				I.JUMP,       # Jump to the end of the block
				Pointer(block_end),
				land_on_error # This is the start of the next case
			)
			land_on_error = Destination()
		self.bytecodeify(args[-1], keys(allow_tco=keys.allow_tco))
		self.push(block_end)

	def btcfy_func_ifelse(self, node, keys, args):
		if len(args) < 3 or len(args) % 2 == 0:
			raise calculator.errors.CompilationError('Invalid number of arguments for ifelse function')
		p_end = Destination()
		p_false = Destination()
		for condition, result in zip(args[::2], args[1::2]):
			self.bytecodeify(condition, keys())
			self.push(I.JUMP_IF_FALSE)
			self.push(Pointer(p_false))
			self.bytecodeify(result, keys(allow_tco=keys.allow_tco))
			self.push(I.JUMP)
			self.push(Pointer(p_end))
			self.push(p_false)
			p_false = Destination()
		self.bytecodeify(args[-1], keys(allow_tco=keys.allow_tco))
		self.push(p_end)

	def btcfy_func_if(self, node, keys, args):
		if len(args) != 3:
			raise calculator.errors.CompilationError('Invalid number of arguments for if function')
		p_end = Destination()
		p_false = Destination()
		self.bytecodeify(args[0], keys())
		self.push(I.JUMP_IF_FALSE)
		self.push(Pointer(p_false))
		self.bytecodeify(args[1], keys(allow_tco=keys.allow_tco))
		self.push(I.JUMP)
		self.push(Pointer(p_end))
		self.push(p_false)
		self.bytecodeify(args[2], keys(allow_tco=keys.allow_tco))
		self.push(p_end)

	def btcfy_func_list(self, node, keys, args,):
		self.push(I.LIST_CREATE_EMPTY)
		for a in args[::-1]:
			self.bytecodeify(a, keys())
			self.push(I.LIST_PREPEND)

	def define_function(self, node, keys):
		# Ensure that none of the parameter names are illigal
		params = [i['string'].lower() for i in node['parameters']['items']]
		for n, i in zip(params, node['parameters']['items']):
			if n in PROTECTED_NAMES:
				m = f'"{n}" is not allowed as a funcation parameter'
				raise calculator.errors.CompilationError(m, i)
		is_macro = int(node.get('kind') == '~>')
		contents = CodeSegment(self.master)
		start_address = Destination()
		# Function header information
		contents.push(
			start_address,                 # Landing place
			node.get('name', '?').lower(), # name
			len(params),                   # number of required parameters
			node.get('variadic', 0),       # whether the function accepts additional parameters
			is_macro                       # whether the function is a macro or not
		)
		# If the function has no parameters, there's no need to add an additional
		# scope frame, since it would hold no information anyway.
		subscope = Scope(params, superscope=keys.scope) if params else keys.scope
		contents.bytecodeify(node['expression'], keys(allow_tco=True, scope=subscope))
		contents.push(
			I.STORE_IN_CACHE,
			I.RETURN
		)
		contents.resolve_jump_addresses()
		return Pointer(start_address)


def ast_to_bytecode(ast, unsafe=False, add_terminal_byte=True) -> ConstructedBytecode:
	builder = Builder()
	segment = builder.build(ast)
	if add_terminal_byte:
		segment.bytecode.append(I.END)
		segment.error_link.append(None)
	return segment


def convert_number(x):
	x = x.lower()
	if x.endswith('i'):
		return sympy.I * convert_number(x[:-1])
	if '.' in x and 'e' not in x:
		i, p = x.split('.')
		k = len(p)
		if k < 30: # Maybe increase this limit
			return sympy.Rational(int(i or '0') * 10 ** k + int(p or '0'), 10 ** k)
	return sympy.Number(x.lstrip('0') or '0')


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
