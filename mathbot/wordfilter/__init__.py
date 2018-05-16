import string
import os

WORDFILE = os.path.dirname(os.path.abspath(__file__)) + '/bad_words.txt'

bad_words = set()

# Load bad words from the file
# Words suffixed with 's' or 'ed' are also considered bad
with open(WORDFILE) as f:
	for i in map(str.strip, f):
		bad_words |= {i, i + 's', i + 'ed'}

def is_bad(sentence):
	# Remove all punctuation from the sentence
	for c in string.punctuation:
		sentence = sentence.replace(c, ' ')
	# See if any of the words are bad
	for word in sentence.lower().split(' '):
		if word in bad_words:
			return True
	return False
