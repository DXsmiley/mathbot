import enum
import calculator.attempt6 as parser
import json


@enum.unique
class I(enum.Enum):
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


class CodeBuilder:

	def __init__(self, offset = 0):
		self.segments = []
		self.offset = offset

	def new_segment(self):
		seg = CodeSegment(self)
		self.segments.append(seg)
		return seg

	def bytecodeify(self, ast):
		self.new_segment().bytecodeify(ast)

	def dump(self):
		bytecode = []
		for i in self.segments:
			bytecode += i.items
		# Determine the location of the destinations
		for address, item in enumerate(bytecode):
			if isinstance(item, Destination):
				item.location = address + self.offset
				bytecode[address] = I.NOTHING
		# Link the pointers up to their destinations
		for address, item in enumerate(bytecode):
			if isinstance(item, Pointer):
				bytecode[address] = bytecode[address].destination.location
		return bytecode


class CodeSegment:

	def __init__(self, builder):
		self.builder = builder
		self.start_address = None
		self.items = []

	def new_segment(self):
		return self.builder.new_segment()

	def push(self, item):
		self.items.append(item)

	def bytecodeify(self, p):
		node_type = p['#']
		if node_type == 'number':
			self.push(I.CONSTANT)
			self.push(convert_number(p['string']))
		elif node_type == 'bin_op':
			self.bytecodeify(p['right'])
			self.bytecodeify(p['left'])
			self.push(OPERATOR_DICT[p['operator']])
		elif node_type == 'not':
			self.bytecodeify(p['expression'])
			self.push(I.UNR_NOT)
		elif node_type == 'die':
			self.bytecodeify(p['faces'])
			self.bytecodeify(p.get('times', {'#': 'number', 'string': '1'}))
			self.push(I.BIN_DIE)
		elif node_type == 'uminus':
			self.bytecodeify(p['value'])
			self.push(I.UNR_MIN)
		elif node_type == 'function_call':
			# Need to determine the function first, because if it's a macro
			# we handle the arguments differently.
			self.bytecodeify(p['function'])
			# This handles normal functions only.
			# Might have to do some more work to also deal with macros.
			args = p.get('arguments', {'items': []})['items']
			jump_end = Destination()
			jump_macro = Destination()
			self.push(I.JUMP_IF_MACRO)
			self.push(Pointer(jump_macro))
			# Handle normal function
			for i in args[::-1]:
				self.bytecodeify(i)
			self.push(I.ARG_LIST_END)
			self.push(len(args))
			self.push(I.JUMP)
			self.push(Pointer(jump_end))
			# Handle macro function
			self.push(jump_macro)
			for i in args[::-1]:
				self.bytecodeify({
					'#': 'function_definition',
					'parameters': {'items': []},
					'kind': '->',
					'expression': i
				})
			self.push(I.ARG_LIST_END)
			self.push(len(args))
			# End of the function call
			self.push(jump_end)
			# self.push(I.CONSTANT)
			# return_location = Destination()
			# self.push(Pointer(return_location))
			# self.push(return_location)
		elif node_type == 'word':
			self.push(I.WORD)
			self.push(p['string'].lower())
		elif node_type == 'factorial':
			self.bytecodeify(p['value'])
			self.push(I.UNR_FAC)
		elif node_type == 'assignment':
			self.bytecodeify(p['value'])
			self.push(I.ASSIGNMENT)
			self.push(p['variable']['string'].lower())
		elif node_type == 'statement_list':
			self.bytecodeify(p['statement'])
			if p['next'] is not None:
				self.bytecodeify(p['next'])
		elif node_type == 'program':
			for i in p['items']:
				self.bytecodeify(i)
			self.push(I.END)
		elif node_type == 'function_definition':
			# Create the function itself
			contents = self.new_segment()
			start_address = Destination()
			contents.push(start_address)
			params = p['parameters']['items']
			contents.push(len(params))
			for i in params:
				contents.push(i['string'].lower())
			contents.push(p.get('variadic', 0))
			contents.bytecodeify(p['expression'])
			contents.push(I.RETURN)
			# Create the bytecode for the current scope
			self.push(I.FUNCTION_MACRO if p['kind'] == '~>' else I.FUNCTION_NORMAL)
			self.push(Pointer(start_address))
		elif node_type == 'comparison': # TODO: THIS
			if len(p['rest']) == 1:
				# Can get away with a simple binary operator like the others
				self.bytecodeify(p['rest'][0]['value'])
				self.bytecodeify(p['first'])
				op = p['rest'][0]['operator']
				self.push(OPERATOR_DICT[op])
			else:
				self.push(I.CONSTANT)
				self.push(1)
				self.bytecodeify(p['first'])
				for i in p['rest']:
					self.bytecodeify(i['value'])
					self.push(COMPARATOR_DICT[i['operator']])
				self.push(I.DISCARD)
			# previous = yield from evaluate_step(p['first'], scope, it)
			# for i in p['rest']:
			# 	op = i['operator']
			# 	current = yield from evaluate_step(i['value'], scope, it)
			# 	if not OPERATOR_DICT[op](previous, current):
			# 		return 0
			# 	previous = current
			# return 1
		else:
			raise Exception('Unknown AST node type: {}'.format(node_type))


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


if __name__ == '__main__':
	tokens, ast = parser.parse('1 + 2')
	print(json.dumps(ast, indent = 4))
	for i in build(ast):
		print(i)
