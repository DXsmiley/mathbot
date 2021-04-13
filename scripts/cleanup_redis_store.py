import sys

import re
import asyncio
import collections
import json
import aioredis
import time
import warnings
import abc


async def connect(url):
    user, password, host, port = re.split(r':|@', url[8:])
    if password == '':
        password = None
    redis = await aioredis.create_redis_pool(
        (host, int(port)),
        password = password,
        db = 1,
        timeout = 5
    )
    print('Connected!')
    return redis


async def iter_all_keys(redis, match):
    cur = b'0'
    while cur:
        cur, keys = await redis.scan(cur, match=match)
        for key in keys:
            yield key


async def groups_of(n, async_generator):
    group = []
    async for i in async_generator:
        if len(group) == n:
            yield group
            group = []
        group.append(i)
    if len(group) != 0:
        yield group


async def purge_blame(redis):
    async for keys in groups_of(20, iter_all_keys(redis, 'blame:*')):
        print(keys)
        await asyncio.gather(*[redis.delete(i) for i in keys])


async def main():
    redis_url = sys.argv[1]
    redis = await connect(redis_url)
    await purge_blame(redis)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
