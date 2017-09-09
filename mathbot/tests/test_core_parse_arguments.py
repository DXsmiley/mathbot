import pytest
import core.parse_arguments


def test_remove_whitespace():
	stack = ['b', ' ', 'a', ' ', '\n', '\t', ' ']
	core.parse_arguments.remove_whitespace(stack)
	assert stack == ['b', ' ', 'a']


def test_break_args():
	assert core.parse_arguments.break_args('') == []
	assert core.parse_arguments.break_args('a b c') == ['a', 'b', 'c']
	assert core.parse_arguments.break_args('hello, world!') == ['hello,', 'world!']
	assert core.parse_arguments.break_args('this "has quotations" in it') == ['this', 'has quotations', 'in', 'it']
	assert core.parse_arguments.break_args('quote "at the end') == ['quote', 'at the end']
