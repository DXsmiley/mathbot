import codecs
import difflib
import os
import os.path
from collections import defaultdict


TOPICS = {} # Mapping of (lang, topic) -> document
PRIMARY_TOPICS = [] # List of primary topics

LANGUAGES = [
	('en', 'English'),
	('en-PT', 'Pirate'),
	('nb-NO', 'Norwegian')
]

CODE_TO_NAME = dict(LANGUAGES)

LANGUAGE_INPUT_MAPPING = {
	**{code.lower(): code for code, name in LANGUAGES},
	**{name.lower(): code for code, name in LANGUAGES}
}


class DuplicateTopicError(Exception):
	def __init__(self, topic):
		self.topic = topic
	def __str__(self):
		return 'Multiple entries for help topic "{}"'.format(self.topic)


def add(topics, language, message, from_file = False):
	if not from_file:
		print('Still using core.help.add for topics', topics)
	if isinstance(topics, str):
		topics = topics.split(' ')
	# The first topic in a list is the 'primary' topic, which gets listed
	if topics[0] != '' and topics[0] not in PRIMARY_TOPICS:
		PRIMARY_TOPICS.append(topics[0])
	if isinstance(message, str):
		message = [message]
	print(f'Adding help document {language} - {" ".join(topics)}')
	for i in topics:
		if (i, language) in TOPICS:
			raise DuplicateTopicError(f'{i} - {language}')
		TOPICS[i, language] = message


def get(topic, language='en'):
	# Fallback for when no translation exists
	did_fallback = False
	if (topic.lower(), language) not in TOPICS:
		language = 'en'
		did_fallback = True
	return (TOPICS.get((topic.lower(), language)), did_fallback)


def listing(language='en'):
	return sorted(PRIMARY_TOPICS[language])


def get_similar(topic, language='en'):
	pt = PRIMARY_TOPICS[language]
	return sorted(difflib.get_close_matches(topic.lower(), pt, len(pt)))


def register(name, topics = None):
	if topics is None:
		topics = []
	for lang in os.listdir('./help'):
		path = os.path.join('./help/', lang)
		if os.path.isdir(path):
			topics, pages = readfile(os.path.join(path, f'{name}.md'))
			add(topics, lang, pages, from_file = True)

def readfile(path):
	pages = [[]]
	topics = []
	with codecs.open(path, 'r', 'utf-8') as f:
		lines = f.readlines()
		for i in map(str.rstrip, lines):
			if i.startswith('#'):
				pages[-1].append('**{}**'.format(i.strip('# ')))
			elif not i.startswith(':::'):
				pages[-1].append(i)
			else:
				command = i[3:].split(' ')
				if command[0] == 'topics':
					topics += list(map(lambda x: x.replace('(blank)', ''), command[1:]))
				elif command[0] == 'page-break':
					# TODO: Automatic page breaks, so translators don't have to deal with them.
					pages.append([])
				else:
					print('Unknown command sequence in help page:', command[0])
		pages = ['\n'.join(lines) for lines in pages]
		for i in pages:
			if len(i) >= 1800:
				print('Help page is too long, add a `:::page-break` to start a new page')
				print('-------------------------------------------------')
				print(i)
				print('-------------------------------------------------')
	return topics, pages

