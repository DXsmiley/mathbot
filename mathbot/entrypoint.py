if __name__ != '__main__':
    
    print('Not main process. Probably crucible?')

    import logging
    logging.basicConfig(level = logging.INFO)

else:
    
    print('Main process starting up')

    import os
    import sys
    import json
    import re
    import bot
    import utils
    import core.parameters
    import aiohttp
    import asyncio
    import time
    import logging
    import warnings

    @utils.apply(core.parameters.load_parameters, list)
    def retrieve_parameters():
        for i in sys.argv[1:]:
            if re.fullmatch(r'\w+\.env', i):
                yield json.loads(os.environ.get(i[:-4]))
            elif i.startswith('{') and i.endswith('}'):
                yield json.loads(i)
            else:
                with open(i) as f:
                    yield json.load(f)

    async def wait_for_slot_in_gateway_queue():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post('http://127.0.0.1:7023/', timeout=5) as resp:
                    wait_until = float(await resp.text())
                    cur_time = time.time()
                    sleep_time = wait_until - cur_time
                    if sleep_time > 0:
                        print(f'Sleeping in gateway queue for {sleep_time} seconds')
                        await asyncio.sleep(sleep_time)
        except aiohttp.ClientConnectorError:
            print('Could not find gateway queue to connect to')

    asyncio.get_event_loop().run_until_complete(wait_for_slot_in_gateway_queue())

    parameters = retrieve_parameters()

    warnings.simplefilter('default')
    logging.basicConfig(level = logging.INFO)
    logging.getLogger('discord.state').setLevel(logging.ERROR)

    bot.run(parameters)
 