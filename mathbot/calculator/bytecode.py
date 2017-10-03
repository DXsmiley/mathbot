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
	FUNCTION_MACRO = 20
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
	CONSTANT_EMPTY_ARRAY = 50

	# Next to use: 55


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


class CodeBuilder:

	def __init__(self, offset = 0):
		self.segments = []
		self.segments_backend = []
		self.offset = offset
		self.globalscope = Scope([])
		self.bytecode = []

	def new_segment(self, late = False):
		seg = CodeSegment(self)
		if late:
			self.segments_backend.append(seg)
		else:
			self.segments.append(seg)
		return seg

	def bytecodeify(self, ast, late = False):
		self.new_segment().bytecodeify(ast, self.globalscope)

	def dump(self):
		newcode = []
		for i in itertools.chain(self.segments, self.segments_backend):
			newcode += i.items
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
		return self.bytecode


class CodeSegment:

	def __init__(self, builder):
		self.builder = builder
		self.start_address = None
		self.items = []

	def new_segment(self, late = False):
		return self.builder.new_segment(late = late)

	def push(self, item):
		self.items.append(item)

	def bytecodeify(self, p, s):
		node_type = p['#']
		if node_type == 'number':
			self.push(I.CONSTANT)
			self.push(convert_number(p['string']))
		elif node_type == 'bin_op':
			self.bytecodeify(p['right'], s)
			self.bytecodeify(p['left'], s)
			self.push(OPERATOR_DICT[p['operator']])
		elif node_type == 'not':
			self.bytecodeify(p['expression'], s)
			self.push(I.UNR_NOT)
		elif node_type == 'die':
			self.bytecodeify(p['faces'], s)
			self.bytecodeify(p.get('times', {'#': 'number', 'string': '1'}), s)
			self.push(I.BIN_DIE)
		elif node_type == 'uminus':
			self.bytecodeify(p['value'], s)
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
				self.bytecodeify(args[0], s)
				self.push(I.JUMP_IF_FALSE)
				self.push(Pointer(p_false))
				self.bytecodeify(args[1], s)
				self.push(I.JUMP)
				self.push(Pointer(p_end))
				self.push(p_false)
				self.bytecodeify(args[2], s)
				self.push(p_end)
			elif function_name == 'map':
				self.bytecodeify(args[0], s)
				self.bytecodeify(args[1], s)
				self.push(I.CONSTANT_EMPTY_ARRAY)
				self.push(I.SPECIAL_MAP)
				self.push(I.STORE_IN_CACHE)
				self.push(I.SPECIAL_MAP_STORE)
			elif function_name == 'reduce':
				self.bytecodeify(args[0], s)
				self.bytecodeify(args[1], s)
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
				self.push(I.STORE_IN_CACHE)
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
					}, s) for i in args[::-1]
				]
				self.bytecodeify(p['function'], s)
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
				self.push(I.STORE_IN_CACHE)
				self.push(I.JUMP)
				self.push(Pointer(landing_end))
				# Handle if macro function
				self.push(landing_macro)
				for i in argument_functions:
					self.push(I.FUNCTION_NORMAL)
					self.push(i)
				self.push(I.ARG_LIST_END)
				self.push(len(args))
				self.push(I.STORE_IN_CACHE)
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
			self.bytecodeify(p['value'], s)
			self.push(I.UNR_FAC)
		elif node_type == 'assignment':
			self.bytecodeify(p['value'], s)
			scope, depth, index = s.find_value(p['variable']['string'].lower())
			assert(scope == self.builder.globalscope)
			# print(scope, depth, index)
			self.push(I.ASSIGNMENT)
			self.push(index)
			# self.push(I.ASSIGNMENT)
			# self.push(p['variable']['string'].lower())
		elif node_type == 'statement_list':
			self.bytecodeify(p['statement'], s)
			if p['next'] is not None:
				self.bytecodeify(p['next'], s)
		elif node_type == 'program':
			for i in p['items']:
				self.bytecodeify(i, s)
			# self.push(I.END)
		elif node_type == 'end':
			self.push(I.END)
		elif node_type == 'function_definition':
			# Create the function itself
			start_pointer = self.define_function(p, s)
			# Create the bytecode for the current scope
			self.push(I.FUNCTION_MACRO if p['kind'] == '~>' else I.FUNCTION_NORMAL)
			self.push(start_pointer)
			return 
		elif node_type == 'comparison':
			if len(p['rest']) == 1:
				# Can get away with a simple binary operator like the others
				self.bytecodeify(p['rest'][0]['value'], s)
				self.bytecodeify(p['first'], s)
				op = p['rest'][0]['operator']
				self.push(OPERATOR_DICT[op])
			else:
				self.push(I.CONSTANT)
				self.push(1)
				self.bytecodeify(p['first'], s)
				for i in p['rest']:
					self.bytecodeify(i['value'], s)
					self.push(COMPARATOR_DICT[i['operator']])
				self.push(I.DISCARD)
		else:
			raise Exception('Unknown AST node type: {}'.format(node_type))

	def define_function(self, p, s):
		contents = self.new_segment(late = True)
		start_address = Destination()
		contents.push(start_address)
		params = [i['string'].lower() for i in p['parameters']['items']]
		contents.push(len(params))
		for i in params:
			contents.push(i)
		contents.push(p.get('variadic', 0))
		if len(params) == 0:
			contents.bytecodeify(p['expression'], s)
		else:
			subscope = Scope(params, superscope = s)
			contents.bytecodeify(p['expression'], subscope)
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
			result.append(i)
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
