# This file handles the bot's parameter loading.

# Parameters in the parameters.json file can be used
# to alter how the bot behaves.


import os
import json
import sys


PREVENT_ARG_PARSING = False


def _dictionary_overwrite(old, new):
	if not isinstance(new, dict):
		return new
	if not isinstance(old, dict):
		return new
	for key in new:
		old[key] = _dictionary_overwrite(old.get(key), new[key])
	return old

def dictionary_overwrite(*dicts):
	result = dicts[0]
	for i in dicts[1:]:
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


def load_parameter_file(filename):
	try:
		with open(filename) as f:
			result = json.loads(f.read())
		return result
	except (FileNotFoundError, PermissionError, IsADirectoryError):
		print('Could not load parameters from file:', filename)
		return {}


def load_parameters(sources):
	dicts = [load_parameter_file('parameters_default.json')]
	for i in sources:
		if i.endswith('.env'):
			ev = os.environ.get(i[:-4])
			# print(ev)
			jdata = json.loads(ev)
			dicts.append(jdata)
		elif i.startswith('{'):
			try:
				dicts.append(json.loads(i))
			except:
				print('Failed to load parameters from argument:')
				print(i)
		else:
			dicts.append(load_parameter_file(i))
	return resolve_parameters(
		dictionary_overwrite(*dicts)
	)


parameters = None


def get(path):
	global parameters
	if parameters is None:
		if PREVENT_ARG_PARSING:
			parameters = load_parameters([])
		else:
			parameters = load_parameters(sys.argv[1:])
	# Break the string down into its components
	path = path.replace('.', ' ').split(' ')
	# Reverse it because popping from the back is much faster
	path = path[::-1]
	result = parameters
	# Follow the path through the parameters and return
	# whatever we end up at
	while len(path) > 0:
		result = result[path.pop()]
	return result
