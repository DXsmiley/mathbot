import enum
import calculator.parser as parser
import calculator.errors
import itertools
import json


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
	WORD = 16
	ASSIGNMENT = 17
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

	SPECIAL_MAP = 48
	SPECIAL_MAP_STORE = 51
	SPECIAL_REDUCE = 49
	SPECIAL_REDUCE_STORE = 52
	SPECIAL_FILTER = 55
	SPECIAL_FILTER_STORE = 56
	CONSTANT_EMPTY_ARRAY = 50

	BEGIN_PROTECTED_GLOBAL_BLOCK = 57
	END_PROTECTED_GLOBAL_BLOCK = 58

	# Next to use: 59


OPERATOR_DICT = {
	'+': I.BIN_ADD,
	'-': I.BIN_SUB,
	'*': I.BIN_MUL,
	'/': I.BIN_DIV,
	'^': I.BIN_POW,
	'%': I.BIN_MOD,
	'&': I.BIN_AND,
	'|': I.BIN_OR_,
	'<': I.BIN_LESS,
	'>': I.BIN_MORE,
	'<=': I.BIN_L_EQ,
	'>=': I.BIN_M_EQ,
	'==': I.BIN_EQUL,
	'!=': I.BIN_N_EQ
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
	'reduce'
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
					'?' if release or e is None else e['position'],
					'?' if release or e is None else e['name']
				])
				if e is not None:
					sources[e['name']] = e['code']
			elif isinstance(i, str):
				result.append(['str', i])
			elif isinstance(i, int):
				result.append(['int', int(i)])
			elif isinstance(i, float):
				result.append(['flt', i])
			elif isinstance(i, complex):
				result.append(['cpx', i.real, i.imag])
			else:
				raise Exception('Unknown bytecode item: {}'.format(str(i)))
		toline = lambda items : ' '.join(map(str, items))
		result = 'bytecode: 0 0 0 (unstable)\n' + '\n'.join(map(toline, result)) + '\n'
		if not release:
			for key, value in sources.items():
				result += 'source: {} {} {}\n{}\n'.format(key, len(value), value.count('\n'), value)
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
		self.new_segment().bytecodeify(ast, self.globalscope, unsafe)

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

	def bytecodeify(self, p, s, unsafe):
		node_type = p['#']
		if node_type == 'number':
			self.push(I.CONSTANT)
			self.push(convert_number(p['string']))
		elif node_type == 'bin_op':
			op = p['operator']
			left = p['left']
			right = p['right']
			if op == '&': # Logical and
				end = Destination()
				self.bytecodeify(left, s, unsafe)
				self.push(
					I.DUPLICATE,
					I.JUMP_IF_FALSE,
					Pointer(end)
				)
				self.bytecodeify(right, s, unsafe)
				self.push(
					I.BIN_AND,
					end
				)
			elif op == '|': # Logical or
				end = Destination()
				self.bytecodeify(left, s, unsafe)
				self.push(
					I.DUPLICATE,
					I.JUMP_IF_TRUE,
					Pointer(end)
				)
				self.bytecodeify(right, s, unsafe)
				self.push(
					I.BIN_OR_,
					end
				)
			else:
				self.bytecodeify(right, s, unsafe)
				self.bytecodeify(left, s, unsafe)
				self.push(OPERATOR_DICT[op], error = p['token']['source'])
		elif node_type == 'not':
			self.bytecodeify(p['expression'], s, unsafe)
			self.push(I.UNR_NOT)
		elif node_type == 'die':
			self.bytecodeify(p['faces'], s, unsafe)
			self.bytecodeify(p.get('times', {'#': 'number', 'string': '1'}), s, unsafe)
			self.push(I.BIN_DIE)
		elif node_type == 'uminus':
			self.bytecodeify(p['value'], s, unsafe)
			self.push(I.UNR_MIN)
		elif node_type == 'function_call':
			args = p.get('arguments', {'items': []})['items']
			function_name = p['function']['string'].lower() if p['function']['#'] == 'word' else None
			if function_name == 'if':
				# Optimisation for the 'if' function.
				if len(args) != 3:
					raise calculator.errors.CompilationError('Invalid number of arguments for if function')
				p_end = Destination()
				p_false = Destination()
				self.bytecodeify(args[0], s, unsafe)
				self.push(I.JUMP_IF_FALSE)
				self.push(Pointer(p_false))
				self.bytecodeify(args[1], s, unsafe)
				self.push(I.JUMP)
				self.push(Pointer(p_end))
				self.push(p_false)
				self.bytecodeify(args[2], s, unsafe)
				self.push(p_end)
			elif function_name == 'ifelse':
				if len(args) < 3 or len(args) % 2 == 0:
					raise calculator.errors.CompilationError('Invalid number of arguments for ifelse function')
				p_end = Destination()
				p_false = Destination()
				for condition, result in zip(args[::2], args[1::2]):
					self.bytecodeify(condition, s, unsafe)
					self.push(I.JUMP_IF_FALSE)
					self.push(Pointer(p_false))
					self.bytecodeify(result, s, unsafe)
					self.push(I.JUMP)
					self.push(Pointer(p_end))
					self.push(p_false)
					p_false = Destination()
				self.bytecodeify(args[-1], s, unsafe)
				self.push(p_end)
			elif function_name == 'map':
				if len(args) != 2:
					raise calculator.errors.CompilationError('Invalid number of argument for map function')
				self.bytecodeify(args[0], s, unsafe)
				self.bytecodeify(args[1], s, unsafe)
				self.push(I.CONSTANT_EMPTY_ARRAY)
				self.push(I.SPECIAL_MAP)
				self.push(I.SPECIAL_MAP_STORE)
			elif function_name == 'filter':
				if len(args) != 2:
					raise calculator.errors.CompilationError('Invalid number of argument for filter function')
				self.bytecodeify(args[0], s, unsafe)
				self.bytecodeify(args[1], s, unsafe)
				self.push(
					I.CONSTANT_EMPTY_ARRAY,
					I.CONSTANT, 0,
					I.SPECIAL_FILTER,
					# I.STORE_IN_CACHE,
					I.SPECIAL_FILTER_STORE
				)
			elif function_name == 'reduce':
				if len(args) != 2:
					raise calculator.errors.CompilationError('Invalid number of argument for reduce function')
				self.bytecodeify(args[0], s, unsafe)
				self.bytecodeify(args[1], s, unsafe)
				# Get the first element of the array
				self.push(I.DUPLICATE)
				self.push(I.CONSTANT)
				self.push(0)
				self.push(I.ACCESS_ARRAY_ELEMENT)
				# Iterator
				self.push(I.CONSTANT)
				self.push(1)
				# Stack now contains [function, array, result, index]
				self.push(I.SPECIAL_REDUCE)
				self.push(I.SPECIAL_REDUCE_STORE)
			else:
				# IDEA: If the function contains only a small amount of code, we can also
				# inline it (for normal function calls). Cannot inline everything since
				# this leads to exponential code growth.
				argument_functions = [
					self.define_function({
						'#': 'function_definition',
						'parameters': {'items': []},
						'kind': '->',
						'expression': i
					}, s, unsafe) for i in args[::-1]
				]
				self.bytecodeify(p['function'], s, unsafe)
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
				self.push(I.ARG_LIST_END)
				self.push(len(args))
				self.push(I.JUMP)
				self.push(Pointer(landing_end))
				# Handle if macro function
				self.push(landing_macro)
				for i in argument_functions:
					self.push(I.FUNCTION_NORMAL)
					self.push(i)
				self.push(I.ARG_LIST_END_NO_CACHE)
				self.push(len(args))
				# Aaaaand we done here
				self.push(landing_end)
		elif node_type == 'word':
			# self.push(I.WORD)
			# self.push(p['string'].lower())
			scope, depth, index = s.find_value(p['string'].lower())
			if scope == self.builder.globalscope:
				# NOTE: Only global variables can fail to be found,
				# so we only need the name for this one.
				self.push(I.ACCESS_GLOBAL)
				self.push(index)
				self.push(p['string'])
			elif depth == 0:
				self.push(I.ACCESS_LOCAL)
				self.push(index)
			else:
				self.push(I.ACCESS_SEMI)
				self.push(depth)
				self.push(index)
		elif node_type == 'factorial':
			self.bytecodeify(p['value'], s, unsafe)
			self.push(I.UNR_FAC)
		elif node_type == 'assignment':
			self.bytecodeify(p['value'], s, unsafe)
			name = p['variable']['string'].lower()
			if name in PROTECTED_NAMES and not unsafe:
				raise calculator.errors.CompilationError('"{}" cannot be assigned to'.format(name))
			scope, depth, index = s.find_value(name)
			assert(scope == self.builder.globalscope)
			# print(scope, depth, index)
			self.push(I.ASSIGNMENT)
			self.push(index)
			# self.push(I.ASSIGNMENT)
			# self.push(p['variable']['string'].lower())
		elif node_type == 'statement_list':
			self.bytecodeify(p['statement'], s, unsafe)
			if p['next'] is not None:
				self.bytecodeify(p['next'], s, unsafe)
		elif node_type == 'program':
			for i in p['items']:
				self.bytecodeify(i, s, unsafe)
			# self.push(I.END)
		elif node_type == 'end':
			self.push(I.END)
		elif node_type == 'function_definition':
			# Create the function itself
			start_pointer = self.define_function(p, s, unsafe)
			# Create the bytecode for the current scope
			# self.push(I.FUNCTION_MACRO if p['kind'] == '~>' else I.FUNCTION_NORMAL)
			self.push(I.FUNCTION_NORMAL)
			self.push(start_pointer)
			return 
		elif node_type == 'comparison':
			if len(p['rest']) == 1:
				# Can get away with a simple binary operator like the others
				self.bytecodeify(p['rest'][0]['value'], s, unsafe)
				self.bytecodeify(p['first'], s, unsafe)
				op = p['rest'][0]['operator']
				self.push(OPERATOR_DICT[op])
			else:
				bailed = Destination()
				end = Destination()
				self.push(I.CONSTANT, 1)
				self.bytecodeify(p['first'], s, unsafe)
				for index, ast in enumerate(p['rest']):
					if index > 0:
						self.push(
							I.STACK_SWAP, # Get the flag on top
							I.DUPLICATE,  # Copy the flag (copy consumed by branch)
							I.JUMP_IF_FALSE, # If its zero, bail
							Pointer(bailed),
							I.STACK_SWAP # Put the value back on top
						)
					self.bytecodeify(ast['value'], s, unsafe)
					self.push(COMPARATOR_DICT[ast['operator']])
				self.push(
					I.JUMP,
					Pointer(end),
					bailed,
					I.STACK_SWAP,
					end,
					I.DISCARD,
				)
		else:
			raise Exception('Unknown AST node type: {}'.format(node_type))

	def define_function(self, p, s, unsafe):
		contents = self.new_segment(late = True)
		start_address = Destination()
		contents.push(start_address)
		contents.push(p.get('name', '?').lower())
		params = [i['string'].lower() for i in p['parameters']['items']]
		for i in params:
			if i in PROTECTED_NAMES:
				raise calculator.errors.CompilationError('"{}" is not allowed as a funcation parameter'.format(i))
		contents.push(len(params))
		# for i in params:
		# 	contents.push(i)
		contents.push(p.get('variadic', 0))
		is_macro = int(p.get('kind') == '~>')
		contents.push(is_macro)
		if len(params) == 0:
			contents.bytecodeify(p['expression'], s, unsafe)
		else:
			subscope = Scope(params, superscope = s)
			contents.bytecodeify(p['expression'], subscope, unsafe)
		if not is_macro:
			contents.push(I.STORE_IN_CACHE)
		contents.push(I.RETURN)
		return Pointer(start_address)


def convert_number(x):
	try:
		try:
			return int(x)
		except Exception:
			return float(x)
	except Exception:
		return complex(x.replace('i', 'j'))


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
			raise Exception('Unknown bytecode item: {}'.format(str(i)))
	return ' '.join(map(str, result))


if __name__ == '__main__':
	tokens, ast = parser.parse('1 + 2')
	print(json.dumps(ast, indent = 4))
	for i in build(ast):
		print(i)
