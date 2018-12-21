import codecs
import difflib


TOPICS = {}
PRIMARY_TOPICS = []


class DuplicateTopicError(Exception):
	def __init__(self, topic):
		self.topic = topic
	def __str__(self):
		return 'Multiple entries for help topic "{}"'.format(self.topic)


def add(topics, message, from_file = False):
	if not from_file:
		print('Still using core.help.add for topics', topics)
	if isinstance(topics, str):
		topics = topics.split(' ')
	# The first topic in a list is the 'primary' topic, which gets listed
	if topics[0] != '':
		PRIMARY_TOPICS.append(topics[0])
	if isinstance(message, str):
		message = [message]
	for i in topics:
		if i in TOPICS:
			raise DuplicateTopicError(i)
		TOPICS[i] = message


def get(topic):
	return TOPICS.get(topic.lower())


def listing():
	return sorted(PRIMARY_TOPICS)


def get_similar(topic):
	return sorted(difflib.get_close_matches(topic.lower(), PRIMARY_TOPICS, len(PRIMARY_TOPICS)))


def load_from_file(filename, topics = None):
	if topics is None:
		topics = []
	pages = [[]]
	with codecs.open(filename, 'r', 'utf-8') as f:
		lines = f.readlines()
		remove_section = False
		for i in map(str.rstrip, lines):
			if remove_section:
				if i.startswith(':::endblock'):
					remove_section = False
			else:
				if i.startswith('#'):
					pages[-1].append('**{}**'.format(i.strip('# ')))
				elif not i.startswith(':::'):
					pages[-1].append(i)
				else:
					command = i[3:].split(' ')
					if command[0] == 'topics':
						topics += command[1:]
					elif command[0] == 'page-break':
						pages.append([])
					elif command[0] == 'endblock':
						pass
					elif command[0] == 'discord':
						pass
					elif command[0] == 'webpage':
						remove_section = True
					else:
						print('Unknown command sequence in help page:', command[0])
		pages = ['\n'.join(lines) for lines in pages]
		for i in pages:
			if len(i) >= 1800:
				print('Help page is too long, add a `:::page-break` to start a new page')
				print('-------------------------------------------------')
				print(i)
				print('-------------------------------------------------')
	add(topics, pages, from_file = True)
