import core.parse_arguments
import pytest

def test_star():
	r = core.parse_arguments.parse('*', 'hello')
	assert(r == ['hello'])

def test_strings():
	r = core.parse_arguments.parse('string string', 'hello world')
	assert(r == ['hello', 'world'])

def test_string_star():
	r = core.parse_arguments.parse('string *', 'hello everybody kek')
	assert(r == ['hello', 'everybody kek'])

def test_integers1():
	r = core.parse_arguments.parse('integer', '7')
	assert(r == [7])

def test_integers2():
	r = core.parse_arguments.parse('integer integer', '83647 -38567')
	assert(r == [83647, -38567])

def test_too_many_args():
	with pytest.raises(core.parse_arguments.InvalidArgumentNumber):
		core.parse_arguments.parse('string string', 'a b c')

def test_too_few_args():
	with pytest.raises(core.parse_arguments.InvalidArgumentNumber):
		core.parse_arguments.parse('string string', 'a')

def test_no_args():
	r = core.parse_arguments.parse('', '')
	assert(r == [])

def test_no_args2():
	r = core.parse_arguments.parse('', '   ')
	assert(r == [])

def test_no_args_excess():
	with pytest.raises(core.parse_arguments.InvalidArgumentNumber):
		core.parse_arguments.parse('', 'a')

def test_misplaced_star():
	with pytest.raises(core.parse_arguments.InvalidGreedyConsumerArgument):
		core.parse_arguments.parse('string * string', 'a b c d e f')

def test_invalid_format():
	with pytest.raises(core.parse_arguments.InvalidFormatError):
		core.parse_arguments.parse('something', 'kek')

def test_invalid_integer1():
	with pytest.raises(core.parse_arguments.InvalidArgumentType):
		core.parse_arguments.parse('integer', 'x')

def test_invalid_integer2():
	with pytest.raises(core.parse_arguments.InvalidArgumentType):
		core.parse_arguments.parse('integer', '1.2')