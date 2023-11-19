# This file handles the bot's parameter loading.

# Parameters in the parameters.json file can be used
# to alter how the bot behaves.


import os
import json
import sys
from pydantic import BaseModel
from typing import Literal, List, Dict, Any, Optional


DEFAULT_PARAMETER_FILE = './mathbot/parameters_default.json'


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
	Parameters.model_validate(default)
	dictionary = resolve_parameters(dictionary_overwrite(default, *sources))
	return Parameters.model_validate(dictionary)


def _load_json_file(filename):
	with open(filename) as f:
		return json.load(f)
	

class KeyStoreModel(BaseModel):
	mode: Literal['memory']


class WolframModel(BaseModel):
	key: str
	

class ErrorReportingModel(BaseModel):
	channel: Optional[str]
	webhook: Optional[str]


class ShardsModel(BaseModel):
	total: int
	mine: List[int]


class CalculatorModel(BaseModel):
	persistent: bool
	libraries: bool


class AdvertisingModel(BaseModel):
	enable: bool
	interval: int
	starting_amount: int


class Parameters(BaseModel):
	release: Literal['development', 'release', 'beta']
	token: str
	keystore: KeyStoreModel
	wolfram: WolframModel
	error_reporting: ErrorReportingModel
	shards: ShardsModel
	calculator: CalculatorModel
	blocked_users: List[int]
	advertising: AdvertisingModel
