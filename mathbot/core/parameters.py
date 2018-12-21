# This file handles the bot's parameter loading.

# Parameters in the parameters.json file can be used
# to alter how the bot behaves.


import os
import json
import sys


DEFAULT_PARAMETER_FILE = 'parameters_default.json'


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
	if not isinstance(sources, list):
		raise TypeError('Sources should be a list')
	default = _load_json_file(DEFAULT_PARAMETER_FILE)
	dictionary = resolve_parameters(dictionary_overwrite(default, *sources))
	return Parameters(dictionary)


def _load_json_file(filename):
	with open(filename) as f:
		return json.load(f)


class Parameters:

	def __init__(self, dictionary):
		self.dictionary = dictionary

	def get(self, path):
		peices = path.replace('.', ' ').split(' ')
		result = self.dictionary
		for i in peices:
			result = result[i]
		return result

	def getd(self, path, default):
		peices = path.replace('.', ' ').split(' ')
		result = self.dictionary
		for i in peices:
			if i not in result:
				return default
			result = result[i]
		return result
