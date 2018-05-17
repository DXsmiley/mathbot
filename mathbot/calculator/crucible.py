''' A small library that uses multiprocessing
	to run small functions that might explode
	in a bad way.
'''

import asyncio
import multiprocessing
import async_timeout
import time


if multiprocessing.get_start_method(allow_none=True) is None:
	# Using the default, 'fork', causes
	# =calc 3^7^7^7^7^7^8^8^7^7^7^8^8^8^7
	# to break, and also the interrupe handlers in
	# bot.py cause issues.
	multiprocessing.set_start_method('spawn')


def child_function(pipe, func, args):
	result = func(*args)
	pipe.send(result)


async def run(function, arguments, timeout=None, raise_on_timeout=True):
	parent_pipe, child_pipe = multiprocessing.Pipe()
	process = multiprocessing.Process(target=child_function, args=(child_pipe, function, arguments), daemon=True)
	try:
		if timeout is None:
			process.start()
			while not parent_pipe.poll():
				await asyncio.sleep(0.001)
			return parent_pipe.recv()
		else:
			async with async_timeout.timeout(timeout):
				process.start()
				while not parent_pipe.poll():
					await asyncio.sleep(0.02)
				return parent_pipe.recv()
	except asyncio.TimeoutError:
		if raise_on_timeout:
			raise
		return None
	finally:
		try:
			process.terminate()
		except Exception:
			pass


if __name__ == '__main__':
	
	def add(a, b):
		return a + b

	def loop():
		for i in range(100000):
			print(i)
			time.sleep(0.1)
	
	# coroutine = run(add, (1, 2), timeout=2)
	coroutine = run(loop, (), timeout=2)
	loop = asyncio.get_event_loop()
	print(loop.run_until_complete(coroutine))
