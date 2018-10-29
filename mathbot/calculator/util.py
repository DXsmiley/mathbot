def foldr(function, sequence, default):
	return functools.reduce(
		lambda a, b: function(b, a),
		sequence[::-1],
		default
	)