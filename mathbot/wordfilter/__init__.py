import string
import itertools
import os
import re


WORDFILE = os.path.dirname(os.path.abspath(__file__)) + '/bad_words.txt'
BAD_WORD_REGEX = None


with open(WORDFILE) as f:
    bad_words = [[word, word + 's', word + 'ed'] for word in map(str.strip, f)]
    BAD_WORD_REGEX = re.compile(
        '|'.join(
            '(' + i[0] + r'1.' + \
            ''.join(j + '..' for j in i[1:-1]) + \
            i[-1] + r'.1' + ')'
            for i in itertools.chain.from_iterable(bad_words)
        )
    )


def is_bad(sentence):
    sentence = sentence.lower()
    marked_characters = [
        ( sentence[i]
        , i == 0 or not sentence[i - 1].isalpha()
        , i == len(sentence) - 1 or not sentence[i + 1].isalpha()
        )
        for i in range(len(sentence)) if sentence[i].isalpha()
    ]
    searchable_string = ''.join([
        c + ('1' if start else '0') + ('1' if end else '0')
        for (c, start, end) in marked_characters
    ])
    return BAD_WORD_REGEX.search(searchable_string) or complex_rules(sentence)


def complex_rules(sentence):
    words = sentence.split()
    return ('rectum' in words and not {'latus', 'semilatus'} & words)
