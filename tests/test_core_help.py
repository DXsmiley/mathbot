import pytest


@pytest.fixture(scope = 'function')
def chelp():
	from mathbot import core
	yield core.help
	core.help.TOPICS = {}


def test_simple(chelp):
	chelp.add('topic', 'message')
	assert chelp.get('topic') == ['message']


def test_empty(chelp):
	assert chelp.get('topic') == None


def test_duplicate(chelp):
	chelp.add('topic', 'message')
	with pytest.raises(chelp.DuplicateTopicError):
		chelp.add('topic', 'message')


def test_array(chelp):
	chelp.add('topic', ['one', 'two'])
	assert chelp.get('topic') == ['one', 'two']


def test_multiple_topics(chelp):
	chelp.add('one two three', 'message')
	assert chelp.get('one') == ['message']
	assert chelp.get('two') == ['message']
	assert chelp.get('three') == ['message']


# TODO: Implement this
# Will need tests to check the various special functions as well
def test_load_from_file(chelp):
	pass
