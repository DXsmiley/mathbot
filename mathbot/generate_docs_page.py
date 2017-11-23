#!/usr/bin/env python3
# encoding: utf-8

import markdown
import core.help
import modules.help

TEMPLATE = '''
<!DOCTYPE html>
<html>
	<head>
		<meta charset="utf-8">
		<link href="https://fonts.googleapis.com/css?family=Inconsolata|Josefin+Sans:300|Titillium+Web:300" rel="stylesheet">
		<link rel="stylesheet" href="style.css">
		<title>MathBot</title>
	</head>
	<body>
		<!-- <div class="navbox">
			<p>
				<a href="#">Support</a>
				<a href="#">Donate</a>
			</p>
		</div> -->
		<div class="doc-nav">
			<a href="index.html"><p>Home</p></a>
			<h1>Docs</h1>
			{links}
		</div>
		<div class="doc-body">
			<div>
				{content}
			</div>
		</div>
	</body>
</html>
'''


REPLACEMENTS = modules.help.CONSTANTS
REPLACEMENTS['prefix'] = '='
REPLACEMENTS['mention'] = '@MathBot'


def process_lines(lines):
	remove_section = False
	for i in lines:
		if remove_section:
			if i.startswith(':::endblock'):
				remove_section = False
		else:
			if i.startswith(':::discord'):
				remove_section = True
			if i.lstrip().startswith('-'):
				yield i.lstrip()
			elif i.startswith('# '):
				pass
			elif not i.startswith(':::'):
				yield i


def get_title(lines, default = '???'):
	for i in lines:
		if i.startswith('# '):
			return i[2:].strip()
	return default


def format_link(topic, title):
	return '<a href="#h-{topic}"><p>{title}</p></a>'.format(
		topic = topic,
		title = title
	)


def run_replacement(line):
	return modules.help.doubleformat(line, **REPLACEMENTS)


def process_topic(topic):
	lines = list(open('./help/{}.md'.format(topic)))
	lines = list(map(run_replacement, lines))
	title = get_title(lines, topic.title())
	title_text = '<h1 id="h-{topic}">{title}</h1>\n\n'.format(
		topic = topic,
		title = title
	)
	lines = ''.join(process_lines(lines))
	return topic, title, title_text + markdown.markdown(lines)


def wrap(blocks):
	blocks = list(blocks)
	return TEMPLATE.format(
		links = '\n\n'.join(format_link(topic, title) for topic, title, _ in blocks),
		content = '\n\n'.join(i for _, _, i in blocks)
	)


def main():
	return wrap(
		map(process_topic, [
			'about',
			'wolfram',
			'latex',
			'calculator',
			'turing',
			'theme',
			'settings',
			'prefix',
			'blame',
			'purge'
		])
	)

string = main()
with open('docs.html', 'w') as f:
	f.write(main())
