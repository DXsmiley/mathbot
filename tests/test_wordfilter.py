import pytest
from mathbot.wordfilter import is_bad

def test_friendly():
	assert not is_bad('Hello, world!')
	assert not is_bad('THESE WORDS ARE FRIENDLY')

def test_malicious():
	assert is_bad('CRAP')
	assert is_bad('oh fuck this')
	assert is_bad('This is shit.')

def test_esoteric():
	assert is_bad('\u200Bfuck')
	assert is_bad('sh\u200Bit')
