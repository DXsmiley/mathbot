''' Utility for automata.

    Allows running tests from a specified module file.

'''

import sys
import os
import importlib.util
import asyncio
import automata

HELP_STRING = '''\
Usage:
    python -m automata target_name token test_cases_module

target_name       - The username of the bot which you want to test
token             - The token used to run the automata bot
test_cases_module - Filename of a python module containing some tests collected with a TestCollector
'''

def _main():
    if len(sys.argv) != 4:
        print(HELP_STRING)
    else:
        _, target_name, token, test_cases_module = sys.argv # pylint: disable=unbalanced-tuple-unpacking
        module_spec = importlib.util.spec_from_file_location("loaded_module", test_cases_module)
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        test_group = None
        for _, value in module.__dict__.items():
            if isinstance(value, automata.TestCollector):
                if test_group is not None:
                    print('Cannot handle multiple TestCollectors in a single file')
                    os.abort()
                test_group = value
        if test_group is None:
            print('Could not find a TestCollector in the supplied module')
            os.abort()

        # Interactive bot
        bot = automata.DiscordUI(target_name, test_group)
        bot.run(token)

        # Exampe to run tests automatically. It ain't easy :(
        # bot = automata.DiscordBot(target_name)
        # loop = asyncio.get_event_loop()
        # print('Running tests automatically...')
        # loop.create_task(bot.start(token))
        # loop.run_until_complete(bot.wait_until_ready())
        # for test in test_group:
        #     print('Running', test.name)
        #     channel = bot.get_channel('134085863150845952')
        #     loop.run_until_complete(bot.run_test(test, channel))
        # loop.run_until_complete(bot.logout())
        # loop.close()


if __name__ == '__main__':
    _main()
