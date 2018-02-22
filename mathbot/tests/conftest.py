import dismock as automata
import bot
import pytest
import asyncio
import core.parameters

from typing import Callable

def pytest_addoption(parser):
    parser.addoption(
        "--run-automata",
        action = "store_true",
        default = False,
        help = "Run tests reliant on the automata"
    )
    parser.addoption(
        "--run-automata-human",
        action = "store_true",
        default = False,
        help = "Run tests reliant on the automata and human interaction"
    )
    parser.addoption(
        "--parameter-file",
        action = "store",
        default = None,
        help = "Load parameters from a file"
    )

###########################################################################
### Stuff neede to shoehorn the automata bot into pytest ##################
###########################################################################


def automata_test(function: Callable[[automata.Interface], None]) \
        -> Callable[[automata.DiscordBot], None]:
    ''' Mark a function as an automata test '''
    @pytest.mark.automata
    @pytest.mark.second
    def _internal(__automata_fixture: automata.DiscordBot) -> None:
        channel_id = core.parameters.get('automata channel')
        channel = __automata_fixture.get_channel(channel_id)
        test = automata.Test(function.__name__, function)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(__automata_fixture.run_test(test, channel))
        loop.run_until_complete(asyncio.sleep(1))
    _internal.__name__ = function.__name__
    return _internal


def automata_test_human(function: Callable[[automata.Interface], None]) \
        -> Callable[[automata.DiscordBot], None]:
    ''' Mark a function as an automata test '''
    @pytest.mark.automata
    @pytest.mark.needs_human
    @pytest.mark.first
    def _internal(__automata_fixture: automata.DiscordBot) -> None:
        if not pytest.config.getoption('--run-automata-human'):
            pytest.skip('Needs --run-automata-human command line option to run human-interaction automata tests.')
        channel_id = core.parameters.get('automata channel')
        channel = __automata_fixture.get_channel(channel_id)
        test = automata.Test(function.__name__, function)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(__automata_fixture.run_test(test, channel))
        loop.run_until_complete(asyncio.sleep(1))
    _internal.__name__ = function.__name__
    return _internal


@pytest.fixture(scope='session')
def __automata_fixture():

    if not pytest.config.getoption('--run-automata'):
        pytest.skip('Needs --run-automata command line option to run automata tests.')

    param_file = pytest.config.getoption('--parameter-file')
    if param_file is None:
        pytest.skip('Needs a specified --parameter-file to run automata tests.')

    loop = asyncio.get_event_loop()

    # TODO: Make this better
    core.parameters.reset()
    core.parameters.add_source_filename(param_file)
    core.parameters.add_source({
        'keystore': {
            'mode': 'disk',
            'disk': {
                'filename': None
            }
        }
    })

    token = core.parameters.get('automata token')
    target = core.parameters.get('automata target')
    channel = core.parameters.get('automata channel')

    if not token:
        pytest.skip('No [automata token] specified.')
    if not target:
        pytest.skip('No [automata target] specified.')
    if not channel:
        pytest.skip('No [automata channel] specified.')

    try:

        if not bot.DONE_SETUP:
            bot.do_setup()

        manager = bot.create_shard_manager(0, 1)
        loop.create_task(manager.run_async())
        auto = automata.DiscordBot(target)
        loop.create_task(auto.start(token))
        loop.run_until_complete(manager.client.wait_until_ready())
        loop.run_until_complete(auto.wait_until_ready())

        yield auto

        loop.run_until_complete(asyncio.sleep(1))
        loop.run_until_complete(manager.client.logout())
        loop.run_until_complete(auto.logout())
        loop.run_until_complete(asyncio.sleep(1))

    finally:

        for task in asyncio.Task.all_tasks():
            task.cancel()
        loop.close()

        core.parameters.reset()
