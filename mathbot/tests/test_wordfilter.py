import pytest
from wordfilter import is_bad

def test():
	assert(not is_bad('Hello, world!'))
	assert(not is_bad('THESE WORDS ARE FRIENDLY'))
	assert(is_bad('CRAP'))
	assert(is_bad('oh fuck this'))
	assert(is_bad('This is shit.'))
