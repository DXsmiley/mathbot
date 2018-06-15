import string
import os


WORDFILE = os.path.dirname(os.path.abspath(__file__)) + '/bad_words.txt'
BAD_WORDS = set()

with open(WORDFILE) as f:
	for i in map(str.strip, f):
		BAD_WORDS |= {i, i + 's', i + 'ed'}


def is_bad(sentence):
	s = sentence.replace('\u200B', '')
	s = ''.join(map(lambda c: c if c in string.ascii_letters else ' ', s))
	return bool(set(s.lower().split(' ')) & BAD_WORDS)
