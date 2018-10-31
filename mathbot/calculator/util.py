from functools import reduce

def foldr(function, sequence, default):
	return reduce(
		lambda a, b: function(b, a),
		sequence[::-1],
		default
	)