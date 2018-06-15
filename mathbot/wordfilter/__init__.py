import string
import os

ASCII_LOWERCASE = set(string.ascii_lowercase)  # fast containment check
WORDFILE = os.path.dirname(os.path.abspath(__file__)) + '/bad_words.txt'
BAD_WORDS = set()

with open(WORDFILE) as f:
	for word in map(str.strip, f):
		BAD_WORDS |= {word, word + 's', word + 'ed'}


def is_bad(sentence):
	words = s.lower().split()
	words = (''.join(map(lambda c: c if c in ASCII_LOWERCASE else '', word)) for word in words)
	return bool(set(words) & BAD_WORDS)
