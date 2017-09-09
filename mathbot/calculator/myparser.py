import json
import re
import random
import types
import collections
import math


def merge(d1, d2, override = False):
	''' Merges two result dictionaries.
		Will throw an error if any non-special keys clash.
	'''
	r = {'__exists__': True}
	for k, v in d1.items():
		r[k] = v
	for k, v in d2.items():
		if k is not '__exists__':
			assert(override or k not in r)
			r[k] = v
	return r
#
# PC_COUTNER = 0

def parse_cache(func):
	''' A decorator to be placed around Item.parse functions
		Caching the result makes the program's runtime polynomial.
	'''
	def replacement(self, left, right, tokens):
		# global PC_COUTNER
		if not hasattr(self, '__parse_cache__'):
			self.__parse_cache__ = {}
		key = (left, right, tokens.identifier)
		if key not in self.__parse_cache__:
			# PC_COUTNER += 1
			# if PC_COUTNER % 10000 == 0:
			# 	print(PC_COUTNER)
			self.__parse_cache__[key] = None
			func_result = func(self, left, right, tokens)
			if isinstance(func_result, types.GeneratorType):
				if tokens.check_ambiguity:
					options = [i for i in list(func_result) if i is not None]
					if len(options) == 0:
						result = None
					elif len(options) == 1:
						result = options[0]
					else:
						result = options[0]
						result['__ambiguous__'] = True
						result['__alternatives__'] = options[1:]
				else:
					result = next(func_result, None)
			else:
				result = func_result
			self.__parse_cache__[key] = result
		return self.__parse_cache__[key]
	return replacement


def is_power_of_two(x):
	return (x & (x - 1)) == 0


# TODO: Finish this off so that splitting by tokens can be faster
class SparseTable:

	def __init__(self, values, default_value, operation):
		self.num_layers = 12 # TODO: Set this dynamically
		self.values = list(values)
		self.default = default_value
		self.operation = operation
		while not is_power_of_two(len(self.values)):
			self.values.append(default_value)
		self.length = len(self.values)
		self.layers = [self.values] + [
			[default_value] * self.length
			for i in range(self.num_layers)
		]
		for e in range(1, self.num_layers):
			for x in range(self.length):
				z = x + 2 ** (e - 1)
				if z < self.length:
					self.layers[e][x] = operation(
						self.layers[e - 1][x],
						self.layers[e - 1][z]
					)
				else:
					self.layers[e][x] = self.layers[e - 1][x]

	# Note that range is inclusive / exclusive
	def get(self, left, right):
		size = right - left
		level = math.ceil(math.log2(size))
		if is_power_of_two(size):
			return self.layers[level][left]
		else:
			return self.operation(
				self.layers[level][left],
				self.layers[level][right - (2 ** (level - 1))]
			)


class Item:

	''' Item base class.
		An 'item' matches some sequence of tokens.
		Items are combined together in order to create complex grammars.
	'''

	width_limit = 1 << 20

	def __init__(self):
		self.complexity = 0

	@parse_cache
	def parse(self, left, right, tokens):
		raise NotImplementedException

	def __add__(self, other):
		return Sequence(self, other)

	def __or__(self, other):
		return Either(self, other)

	def __invert__(self):
		return Optional(self)

	def __call__(self, string):
		name = None
		item = self
		values = {}
		for i in string.split():
			# TODO: Change this to 'tag'?
			if i[0] == '#':
				assert('type' not in values)
				values['type'] = i[1:]
			elif '=' in i:
				key, value = i.split('=')
				assert(key not in values)
				values['type'] = value
			else:
				assert(name is None)
				name = i
		if len(values) > 0:
			item = Attach(item, values)
		if name is not None:
			item = NamedItem(item, name)
		return item

	def cache_purge(self, seen, identifier):
		if self not in seen:
			seen.add(self)
			if hasattr(self, '__parse_cache__'):
				if identifier is None:
					self.__parse_cache__ = {}
				else:
					for key in list(self.__parse_cache__):
						if key[2] == identifier:
							del self.__parse_cache__[key]
			for key, value in self.__dict__.items():
				if isinstance(value, Item):
					value.cache_purge(seen, identifier)

	def collect_tokens(self, seen = None):
		if seen is None:
			seen = set()
		if self not in seen:
			seen.add(self)
			for key, value in self.__dict__.items():
				if isinstance(value, Item):
					yield from value.collect_tokens(seen)


class Defer(Item):

	''' Used to create recursion within the grammar.
		Defer is used to seperate the declaration of a rule from its definition.
	'''

	def __lshift__(self, item):
		self.item = item

	def parse(self, left, right, tokens):
		return self.item.parse(left, right, tokens)


class Attach(Item):

	''' Used to attach additional information to a rule.
		This is incredibly usefull when looking at the syntax tree later.
	'''

	def __init__(self, item, data, override = False):
		self.complexity = item.complexity + 1
		self.item = item
		self.data = data
		self.override = override

	def parse(self, left, right, tokens):
		result = self.item.parse(left, right, tokens)
		if result:
			return merge(result, self.data, override = self.override)

	def tmatch(self, string):
		yield from self.item.tmatch(string)


class Repeat(Item):

	''' Matches one or more instances of an item. '''

	def __init__(self, item):
		self.complexity = (item.complexity + 1) * 2
		self.item = item
		# self.minimum = minimum
		# self.maximum = maximum

	@parse_cache
	def parse(self, left, right, tokens):
		if left != right:
			for split in range(left + 1, right):
				res1 = self.item.parse(left, split, tokens)
				if res1:
					res2 = self.parse(split, right, tokens)
					if res1 and res2:
						yield {
							'count': res2['count'] + 1,
							'items': [res1] + res2['items']
						}
			res = self.item.parse(left, right, tokens)
			if res:
				yield {
					'count': 1,
					'items': [res]
				}


class Alternate(Item):

	''' Matches two 'alternating' items.
		Usefull for comma-delimited lists and such.
		Note that that this matches one or more instances of 'item',
		seperated by a single instance of 'delim'
	'''

	def __init__(self, item, delim, supress_delimiter = True, min_count = 0):
		self.complexity = (min(item.complexity, delim.complexity) + 1) * 2
		self.supress_delimiter = supress_delimiter
		self.internal = item('first') + ~(Repeat(delim('delimiter') + item('item'))('rest'))
		self.min_count = min_count

	@parse_cache
	def parse(self, left, right, tokens):
		# IDEA: Does this throw away any ambigous possibilities?
		res = self.internal.parse(left, right, tokens)
		if res:
			first = res.get('first')
			rest = res.get('rest', {'count': 0, 'items': []})
			if first:
				items = [first]
				for i in rest['items']:
					if not self.supress_delimiter:
						items.append(i['delimiter'])
					items.append(i['item'])
				count = rest['count'] * 2 + 1
				if count >= self.min_count:
					yield {
						'count': count,
						'items': items
					}


class NamedItem(Item):

	''' A named item. '''

	def __init__(self, item, name):
		self.complexity = item.complexity + 1
		self.item = item
		self.name = name

	def parse(self, left, right, tokens):
		result = self.item.parse(left, right, tokens)
		if result:
			return {self.name: result}

	# This is so that names tokens work inside DivideByToken
	def tmatch(self, string):
		yield from self.item.tmatch(string)


class TokenItem(Item): pass


class Token(TokenItem):

	''' Will match a fixed set of strings. '''

	def __init__(self, *items):
		self.complexity = 1
		self.width_limit = 1
		self.items = set(items)

	def parse(self, left, right, tokens):
		if left == right - 1 and tokens[left] in self.items:
			tokens.update_rightmost(left)
			return {
				'place': left,
				'token': tokens[left]
			}

	def match(self, string):
		for i in self.items:
			if string.startswith(i):
				yield i

	def tmatch(self, string):
		if string in self.items:
			yield string

	def collect_tokens(self, seen):
		if self not in seen:
			seen.add(self)
			yield self


class ReToken(TokenItem):

	''' Will match a fixed set of regexes. '''

	def __init__(self, *items):
		self.complexity = len(items)
		self.width_limit = 1
		self.items = list(map(re.compile, items))

	def parse(self, left, right, tokens):
		if left == right - 1:
			for regex in self.items:
				if re.fullmatch(regex, tokens[left]):
					tokens.update_rightmost(left)
					return {
						'place': left,
						'token': tokens[left]
					}

	def match(self, string):
		for regex in self.items:
			match = re.match(regex, string)
			if match != None:
				match = match.group()
				if match != '':
					yield match

	# TODO: Fix this up. Needs to match whole string.
	def tmatch(self, string):
		for regex in self.items:
			match = re.match(regex, string)
			if match != None:
				match = match.group()
				if match != '':
					yield match

	def collect_tokens(self, seen):
		if self not in seen:
			seen.add(self)
			yield self


class Optional(Item):

	''' Matches nothing, or the item its given. '''

	def __init__(self, item):
		self.complexity = item.complexity + 1
		self.item = item

	@parse_cache
	def parse(self, left, right, tokens):
		if left == right:
			yield {'__exists__': True}
		yield self.item.parse(left, right, tokens)


COUNTER = 0

class Sequence(Item):

	''' Matches two consecutive items. '''

	def __init__(self, first, second):
		self.width_limit = first.width_limit + second.width_limit
		self.complexity = min(first.complexity, second.complexity) + 1
		# super(Sequence, self)
		self.first = first
		self.second = second

	@parse_cache
	def parse(self, left, right, tokens):
		global COUNTER
		if right - left <= self.width_limit:
			start = max(left, right - self.second.width_limit)
			end   = min(right, left + self.first.width_limit)
			for split in range(start, end + 1):
				# COUNTER += 1
				# if COUNTER % 100000 == 0:
				# 	print(COUNTER)
				res1 = self.first.parse(left, split, tokens)
				if res1:
					res2 = self.second.parse(split, right, tokens)
					if res2:
						yield merge(res1, res2)
			# 'optimal' ordering has been disabled here
			# if self.first.complexity < self.second.complexity:
			# 	for split in range(start, end + 1):
			# 		COUNTER += 1
			# 		if COUNTER % 100000 == 0:
			# 			print(COUNTER)
			# 		res1 = self.first.parse(left, split, tokens)
			# 		if res1:
			# 			res2 = self.second.parse(split, right, tokens)
			# 			if res2:
			# 				yield merge(res1, res2)
			# else:
			# 	for split in range(start, end + 1):
			# 		COUNTER += 1
			# 		if COUNTER % 100000 == 0:
			# 			print(COUNTER)
			# 		res2 = self.second.parse(split, right, tokens)
			# 		if res2:
			# 			res1 = self.first.parse(left, split, tokens)
			# 			if res1:
			# 				yield merge(res1, res2)


class Either(Item):

	''' Matches one of two items. '''

	def __init__(self, first, second):
		self.first = first
		self.second = second
		if first.complexity > second.complexity:
			self.first = second
			self.second = first
		self.complexity = first.complexity + second.complexity + 1

	@parse_cache
	def parse(self, left, right, tokens):
		res1 = self.first.parse(left, right, tokens)
		if res1:
			yield res1
		res2 = self.second.parse(left, right, tokens)
		if res2:
			yield res2

	def tmatch(self, string):
		yield from self.first.tmatch(string)
		yield from self.second.tmatch(string)


class Supress(Item):

	''' Supresses the results of a match, effectively ignoring the details. '''

	def __init__(self, item):
		self.complexity = item.complexity + 1
		self.item = item

	def parse(self, left, right, tokens):
		res = self.item.parse(left, right, tokens)
		if res:
			return {'__exists__': True}

	def tmatch(self, string):
		yield from self.item.match(string)


class BailOnToken(Item):

	'''Bails out if some tokens do or do not exist in the range.'''

	def __init__(self, item, required = set(), forbidden = set()):
		self.complexity = item.complexity + 1
		self.required = required
		self.forbidden = forbidden
		self.item = item

	@parse_cache
	def parse(self, left, right, tokens):
		t = {tokens[i] for i in range(left, right)}
		if t & self.required == self.required and not t & self.forbidden:
			return self.item.parse(left, right, tokens)


class EnsureBalanced(Item):

	'''Bails out if things like brackets look imbalanced.'''

	def __init__(self, item, topen, tclose, cache = None):
		self.complexity = item.complexity + 1
		self.item = item
		self.open = topen
		self.close = tclose
		self.cache = {} if cache is None else cache
		# print(id(self.cache))

	def parse(self, left, right, tokens):
		if self.count_balance(left, right, tokens) == 0:
			return self.item.parse(left, right, tokens)

	def count_balance(self, left, right, tokens):
		if left == right:
			return 0
		key = (left, right, tokens.identifier)
		if key not in self.cache:
			# print('{:3d} {:3d}'.format(left, right), key, id(self.cache))
			value = self.count_balance(left, right - 1, tokens)
			if tokens[right - 1] == self.open:
				value += 1
			elif tokens[right - 1] == self.close:
				value -= 1
			if value < 0:
				value = -100
			self.cache[key] = value
		return self.cache[key]

	def cache_purge(self, seen, identifier):
		if self not in seen:
			seen.add(self)
			for key in list(self.cache):
				if identifier is None or key[2] == identifier:
					del self.cache[key]
			for key, value in self.__dict__.items():
				if isinstance(value, Item):
					value.cache_purge(seen, identifier)

# TODO: Change to binary search
def find_first_ge(l, x):
	for v in l:
		if v >= x:
			return v

# TODO: Change to binary search
def find_last_lt(l, x):
	for i in range(len(l) - 1, -1, -1):
		if l[i] < x:
			return l[i]

class DivideByToken(Item):

	def __init__(self, first, delimiter, second, direction = 'left'):
		self.complexity = first.complexity + second.complexity + 1
		self.first = first
		self.delimiter = delimiter
		self.second = second
		self.direction = direction
		self.cache = {} # TODO: Replace with weak reference dictionary

	@parse_cache
	def parse(self, left, right, tokens):
		if right > left:
			# Find all the tokens that match out delimiter if we haven't
			# already done so
			if tokens not in self.cache:
				self.cache[tokens] = collections.defaultdict(list)
				level = 0
				for i, v in enumerate(tokens.tokens):
					if v == '(':
						level += 2
					elif v == ')':
						level -= 2
					else:
						if next(self.delimiter.tmatch(v), False):
							self.cache[tokens][level].append(i)
			# Find the token that we need to split at
			level = tokens.get_minimum_level(left, right)
			split_place = None
			if self.direction == 'left':
				split_place = find_first_ge(self.cache[tokens][level], left)
			else:
				split_place = find_last_lt(self.cache[tokens][level], right)
			# Properly parse the pieces and yield the result if the
			# sections parse
			if split_place is not None and left <= split_place < right:
				r1 = self.first.parse(left, split_place, tokens)
				if r1:
					r2 = self.second.parse(split_place + 1, right, tokens)
					if r2:
						t = self.delimiter.parse(split_place, split_place + 1, tokens)
						if t:
							yield merge(r1, merge(r2, t))


class TokenObject:

	''' Stores a sequence of tokens, as well as some information
		to help track and debug the parsing process.
	'''

	id_counter = 0

	def __init__(self, tokens):
		self.identifier = TokenObject.id_counter
		TokenObject.id_counter += 1
		self.tokens = tokens
		self.rightmost = 0
		self.check_ambiguity = False
		self.levels = []

		# Calculate token levels
		level = 0
		for i in self.tokens:
			if i == '(':
				self.levels.append(level + 1)
				level += 2
			elif i == ')':
				self.levels.append(level - 1)
				level -= 2
			else:
				self.levels.append(level)

		self.levels_table = SparseTable(self.levels, max(self.levels), min)

	def update_rightmost(self, place):
		self.rightmost = max(self.rightmost, place + 1)

	def get_minimum_level(self, left, right):
		return self.levels_table.get(left, right + 1)

	def find_splitter_token(self, left, right, token_item, direction = 'left'):
		# assert(isinstance(token_item, TokenItem))
		level = self.get_minimum_level(left, right)
		r = range(left, right) if direction == 'left' else range(right - 1, left - 1, -1)
		for i in r:
			if self.levels[i] == level:
				item = next(token_item.tmatch(self.tokens[i]), None)
				if item:
					return i

	def __getitem__(self, index):
		return self.tokens[index]


class Master(Item):

	def __init__(self, item):
		self.complexity = item.complexity + 1
		self.item = item

	@parse_cache
	def parse(self, left, right, tokens):
		return self.item.parse(left, right, tokens)


class Language:

	def __init__(self, grammar):
		self.grammar = Master(grammar)
		self.tokens = list(self.grammar.collect_tokens())

	def cache_purge(self, identifier = None):
		self.grammar.cache_purge(set(), identifier)


def is_ambiguous(tree):
	if isinstance(tree, dict):
		if '__ambiguous__' in tree:
			return True
		else:
			for key, value in tree.items():
				if is_ambiguous(value):
					return True
	return False


TRIM_LIMIT = 40


class ProcessingFailure(Exception):

	def __init__(self, string, consumed):
		self.string = string
		self.consumed = consumed
		self.trim()

	def trim(self):
		start_excess = max(0, self.consumed - TRIM_LIMIT)
		if start_excess > 3:
			self.string = '...' + self.string[start_excess:]
			self.consumed -= start_excess
		end_excess = max(0, len(self.string) - TRIM_LIMIT * 2)
		if end_excess > 3:
			self.string = self.string[:TRIM_LIMIT * 2] + '...'

	def __str__(self):
		return self.string + '\n' + ' ' * self.consumed + '^'


class TokenizationFailed(ProcessingFailure): pass
class ParseFailed(ProcessingFailure): pass


def tokenize(tokens, string):
	result = []
	# Hard coded thing here, maybe remove it.
	string = string.replace('\n', ' ').replace('\t', ' ')
	original_string = string
	while len(string) > 0:
		# print(string)
		if string[0] == ' ':
			string = string[1:]
		else:
			possible = []
			for i in tokens:
				# print(i)
				possible += list(i.match(string))
			# print(possible)
			possible.sort(key = len, reverse = True)
			if len(possible) == 0:
				raise TokenizationFailed(original_string, len(original_string) - len(string))
			result.append(possible[0])
			string = string[len(possible[0]):]
	return result


def parse(language, string, check_ambiguity = True):
	tokens = tokenize(language.tokens, string)
	# print(tokens)
	to = TokenObject(tokens)
	to.check_ambiguity = check_ambiguity
	result = language.grammar.parse(0, len(tokens), to)
	language.cache_purge(to.identifier)
	if result is None:
		raise ParseFailed(' '.join(tokens), sum(map(len, tokens[:to.rightmost])) + to.rightmost)
	# print(to.rightmost)
	# print(' '.join(tokens))
	# print((sum(map(len, tokens[:to.rightmost])) + to.rightmost) * ' ' + '^')
	return to, result


# if __name__ == '__main__':
#
# 	tokens = 'the cat ate everything'.split()
#
# 	proper_noun = Attach(Token('everything') | Token('nothing') | Token('Steven'), {'noun_type': 'proper'})
# 	noun = Attach(Token('cat') | Token('floor'), {'noun_type': 'improper'})
# 	verb = Token('ate') | Token('destroyed')
# 	noun_in_use = (Token('the')('particle') + noun('noun')) | proper_noun
# 	sentence = noun_in_use('n1') + verb('verb') + noun_in_use('n2')
#
# 	result = run(sentence, tokens)
# 	print(json.dumps(result, indent = 4))

# if __name__ == '__main__':
#
# 	tokens = list('*****,**,*****,******,****')
#
# 	stars = Repeat(Token('*'))
# 	csv = stars('first') + Repeat(Token(',')('comma') + stars('stars'))('rest')
# 	# print(run(stars, list('******')))
# 	result = run(csv, tokens)
# 	print(json.dumps(result, indent = 4))
