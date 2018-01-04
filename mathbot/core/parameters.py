# This file handles the bot's parameter loading.

# Parameters in the parameters.json file can be used
# to alter how the bot behaves.


import os
import json
import sys


def _dictionary_overwrite(old, new):
	if not isinstance(new, dict):
		return new
	if not isinstance(old, dict):
		return new
	for key in new:
		old[key] = _dictionary_overwrite(old.get(key), new[key])
	return old


def dictionary_overwrite(*dicts):
	result = [{}]
	for i in dicts:
		result = _dictionary_overwrite(result, i)
	return result


def resolve_parameters(params):
	if isinstance(params, dict):
		return {key : resolve_parameters(value) for key, value in params.items()}
	elif isinstance(params, list):
		return [resolve_parameters(i) for i in params]
	elif isinstance(params, str):
		if params.startswith('env:'):
			return os.environ.get(params[4:])
		if params.startswith('escape:'):
			return params[7:]
	return params


def load_parameters(sources):
	return resolve_parameters(
		dictionary_overwrite(*sources)
	)


parameters = None
sources = []


def add_source(value):
	global sources
	if parameters:
		raise Exception('Cannot add parameter source after parameters have been loaded')
	sources.append(value)


def add_source_filename(filename):
	with open(filename) as f:
		add_source(json.load(f))


add_source_filename('parameters_default.json')


def get(path):
	global parameters
	if parameters is None:
		parameters = load_parameters(sources)
	# Break the string down into its components
	path = path.replace('.', ' ').split(' ')
	# Reverse it because popping from the back is much faster
	path = path[::-1]
	# Follow the path through the parameters and return
	# whatever we end up at
	result = parameters
	while len(path) > 0:
		result = result[path.pop()]
	return result
