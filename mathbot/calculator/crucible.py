'''
	A small library that uses multiprocessing
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
	print('Crucible set multiprocessing start method')


def worker(pipe):
	while True:
		if pipe.poll():
			func, args = pipe.recv()
			pipe.send(func(*args))
			del func, args
		time.sleep(0.1)


class Process:

	__slots__ = ['_pipe', '_process']

	def __init__(self):
		self._pipe, child_pipe = multiprocessing.Pipe()
		self._process = multiprocessing.Process(target=worker, args=(child_pipe,), daemon=True)
		self._process.start()

	def send(self, value):
		self._pipe.send(value)

	def recv(self):
		return self._pipe.recv()

	def poll(self):
		return self._pipe.poll()

	def terminate(self):
		self._process.terminate()


class Pool:

	__slots__ = ['_semaphore', '_idle']

	def __init__(self, max_processess):
		self._semaphore = asyncio.Semaphore(max_processess)
		self._idle = []

	def _get_process_for_use(self):
		if self._idle:
			return self._idle.pop()
		return Process()

	async def run(self, function, arguments, *, timeout=5):
		proc = None
		result = None
		async with self._semaphore:
			try:
				proc = self._get_process_for_use()
				async with async_timeout.timeout(timeout):
					proc.send((function, arguments))
					while not proc.poll():
						await asyncio.sleep(0.01)
					result = proc.recv()
			except asyncio.TimeoutError:
				try:
					proc.terminate()
				except Exception:
					pass
				raise
			else:
				self._idle.append(proc)
		return result


GLOBAL_POOL = Pool(4)
async def run(function, arguments, *, timeout=5):
	return await GLOBAL_POOL.run(function, arguments, timeout=timeout)


def large():
	print('Being large...')
	large = 10000000
	return large ** large


def small(x):
	return x * x


async def guard(f):
	start = time.time()
	try:
		return await f
	except Exception as e:
		print('Guard', time.time() - start)

async def many():
	return sum(await asyncio.gather(*[run(small, (i,), timeout=1) for i in range(100)]))


if __name__ == '__main__':
	coroutine = asyncio.gather(
		guard(run(large, (), timeout=2)),
		many(),
		guard(run(large, (), timeout=3)),
		many(),
		guard(run(large, (), timeout=4)),
		many(),
		guard(run(large, (), timeout=5)),
		many(),
	)
	loop = asyncio.get_event_loop()
	print(loop.run_until_complete(coroutine))
