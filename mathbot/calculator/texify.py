import calculator.calculator
import calculator.myparser

class BindingBrakcets:

	def __init__(self):
		self.strength = 0
		self.internal = 0

	def __lshift__(self, other):
		self.internal = max(self.internal, other)

	def __str__(self):
		if self.strength < self.internal:
			return '('
		else:
			return ''

	def close(self):
		if self.strength < self.internal:
			return ')'
		else:
			return ''

def wrap_p(generator):
	yield r'\left('
	result = yield from generator
	yield r'\right)'
	return result

def wrap_b(generator):
	yield r'{'
	result = yield from generator
	yield r'}'
	return result

def interleave_from(generator, symbol):
	not_first = False
	for i in generator:
		if not_first:
			yield symbol
		else:
			not_first = True
		yield from i

def interleave(generator, symbol):
	not_first = False
	for i in generator:
		if not_first:
			yield symbol
		else:
			not_first = True
		yield i

SPECIAL_NAMES = {
	'sin': r'\sin',
	'cos': r'\cos',
	'tan': r'\tan'
}

def texify(p):
	binding = BindingBrakcets()
	binding.strength = 999
	yield binding
	if p['type'] == 'number':
		yield p['token']
	elif p['type'] == 'binop':
		op = p['operator']['token']
		left = texify(p['left'])
		right = texify(p['right'])
		if op == '/':
			yield r'\frac'
			yield from wrap_b(left)
			yield from wrap_b(right)
		elif op == '*':
			binding << (yield from left)
			yield '\cdot'
			binding << (yield from right)
		elif op == '^':
			binding << (yield from left)
			yield '^'
			yield from wrap_b(right)
		else:
			binding << (yield from left)
			yield op
			binding << (yield from right) + 0.00001
	elif p['type'] == 'udie':
		binding.strength = 2
		yield 'd'
		binding << (yield from texify(p['faces']))
	elif p['type'] == 'uminus':
		binding.strength = 3
		yield '-'
		binding << (yield from texify(p['value']))
	elif p['type'] == 'function_call':
		yield from texify(p['function'])
		arguments = p.get('arguments', {'items': []})['items']
		yield from wrap_p(interleave_from(map(texify, arguments), ','))
	elif p['type'] == 'word':
		t = p['token']
		yield SPECIAL_NAMES.get(t, t)
	elif p['type'] == 'factorial':
		binding << (yield from texify(p['value']))
		yield '!'
	elif p['type'] == 'assignment':
		yield p['variable']['token']
		yield '='
		yield from texify(p['value'])
	elif p['type'] == 'program':
		for i in p.get('statements', {'items': []})['items']:
			yield from texify(i)
			yield r'\\'
		if 'expression' in p:
			yield from texify(p['expression'])
	elif p['type'] == 'function_definition':
		parameters = p.get('parameters', {'items': []})
		parameters = [i['token'] for i in parameters['items']]
		yield from wrap_p(interleave(parameters, ','))
		if p['operator']['token'] == '->':
			yield r'\to'
		else:
			yield r'\leadsto'
		yield from wrap_p(texify(p['expression']))
	else:
		print('Cannot texify:', p['type'])
	assert(bool(str(binding)) == bool(binding.close()))
	yield binding.close()
	return binding.strength
	# elif p['type'] == 'comparison':
	# 	assert(p['count'] > 1)
	# 	previous = yield from evaluate_step(p['items'][0], scope)
	# 	for i in range(1, len(p['items']), 2):
	# 		op = p['items'][i]['token']
	# 		current = yield from evaluate_step(p['items'][i + 1], scope)
	# 		if op == '<':
	# 			compared = previous < current
	# 		elif op == '>':
	# 			compared = previous > current
	# 		elif op == '<=':
	# 			compared = previous <= current
	# 		elif op == '>=':
	# 			compared = previous >= current
	# 		elif op == '==':
	# 			compared = (previous == current)
	# 		elif op == '!=':
	# 			compared = (previous != current)
	# 		if not compared:
	# 			return False
	# 		previous = current
	# 	return True
	# elif p['type'] == 'output':
	# 	result = yield from evaluate_step(p['expression'], scope)
	# 	print(result)
	# 	return result

def process(equation):
	to, result = calculator.myparser.parse(calculator.calculator.GRAMMAR, equation)
	assert(result is not None)
	result = list(texify(result))
	for i in result:
		print(i)
	return ' '.join(map(str, result))
