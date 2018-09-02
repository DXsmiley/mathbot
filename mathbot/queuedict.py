'''
	Dictionary class whose items are deleted after a certain time.
	Inspired by: https://github.com/mailgun/expiringdict/blob/master/expiringdict/__init__.py
	however this is more agressive with deleting things.

	Note that it is unsafe to use the following pattern:

		if key in mydict:
			mydict[key]

	Since the key may be deleted between the time that it is initially checked,
	and when it is subsequently used.

'''

import collections
import time

class QueueDict:

	def __init__(self, *, timeout=120, max_size=None):
		self._dict = collections.OrderedDict()
		self._timeout = timeout
		self._max_size = max_size

	def __contains__(self, key):
		self._cleanup()
		return key in self._dict

	def __setitem__(self, key, value):
		self._cleanup()
		curtime = int(time.time())
		self._dict[key] = (curtime, value)
		self._dict.move_to_end(key, last=False)

	def __getitem__(self):
		self._cleanup()
		return self._dict[key][1]

	def __delitem__(self, key):
		del self._dict[key]
		self._cleanup()

	def get(self, key, default=None):
		self._cleanup()
		return self._dict.get(key, (None, default))[1]

	def pop(self, key, default=None):
		self._cleanup()
		return self._dict.pop(key, (None, default))[1]

	def _cleanup(self):
		while self._max_size and len(self._dict) > self._max_size:
			self._dict.popitem(last=True)
		while self._dict:
			curtime = int(time.time())
			key, (keytime, value) = self._dict.popitem(last=True)
			if curtime - keytime < self._timeout:
				self._dict[key] = (keytime, value)
				self._dict.move_to_end(key, last=True)
				break

	def __str__(self):
		return f'QueueDict({self._dict})'
