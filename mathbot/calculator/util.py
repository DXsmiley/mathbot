from functools import reduce, wraps

def foldr(function, sequence, default):
	return reduce(
		lambda a, b: function(b, a),
		sequence[::-1],
		default
	)

def tail_recursive(function):
	@wraps(function)
	def internal(*args, **kwargs):
		try:
			nf, na = next(function(*args, **kwargs))
			while True:
				nf, na = nf(*na)
		except StopIteration as e:
			return e.value
	return internal
