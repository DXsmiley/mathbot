''' Test the bot by running an instance of it and interfacing
    with it through Discord itself.
'''

# pylint: disable=missing-docstring

import automata
import bot
import pytest
import asyncio
import core.parameters
import pytest

from typing import Callable


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


###########################################################################
### The Actual Tests ######################################################
###########################################################################


# @auto.setup()
# async def setup(interface):
#     await interface.wait_for_reply('=set channel f-delete-tex original')
#     await interface.wait_for_reply('=set server  f-delete-tex original')
#     await interface.wait_for_reply('=set channel f-inline-tex original')
#     await interface.wait_for_reply('=set server  f-inline-tex original')
#     await interface.wait_for_reply('=set channel f-calc-shortcut original')
#     await interface.wait_for_reply('=set server  f-calc-shortcut original')


# @automata_test
# async def test_sample(interface):
#     assert True


@automata_test
async def test_addition(interface):
    await interface.assert_reply_equals('=calc 2+2', '4')


@automata_test
async def test_calc_shortcut(interface):
    await interface.assert_reply_equals('== 8 * 9', '72')


@automata_test
async def test_calc_settings(interface):
    await interface.assert_reply_equals('== 2*3', '6')
    await interface.assert_reply_contains('=set channel f-calc-shortcut disable', 'applied')
    await interface.send_message('== 5-3')
    await interface.ensure_silence()
    await interface.assert_reply_contains('=set channel f-calc-shortcut original', 'applied')
    await interface.assert_reply_equals('== 8/2', '4')


@automata_test
async def test_permissions(interface):
    err = 'That command may not be used in this location.'
    await interface.assert_reply_contains('=set channel c-calc original', 'applied')
    await interface.assert_reply_contains('=set server c-calc original', 'applied')
    await interface.assert_reply_equals('=calc 1+1', '2')
    await interface.assert_reply_contains('=set channel c-calc disable', 'applied')
    await interface.assert_reply_equals('=calc 1+1', err)
    await interface.assert_reply_contains('=set server c-calc disable', 'applied')
    await interface.assert_reply_equals('=calc 1+1', err)
    await interface.assert_reply_contains('=set channel c-calc enable', 'applied')
    await interface.assert_reply_equals('=calc 1+1', '2')
    await interface.assert_reply_contains('=set channel c-calc original', 'applied')
    await interface.assert_reply_equals('=calc 1+1', err)
    await interface.assert_reply_contains('=set server c-calc original', 'applied')
    await interface.assert_reply_equals('=calc 1+1', '2')


@automata_test
async def test_latex(interface):
    for message in ['=tex Hello', '=tex\nHello', '=tex `Hello`']:
        await interface.send_message(message)
        response = await interface.wait_for_message()
        assert len(response.attachments) == 1


@automata_test_human
async def test_latex_settings(interface):
    await interface.send_message('=theme light')
    await interface.wait_for_message()
    await interface.send_message(r'=tex \text{This should be light}')
    response = await interface.wait_for_message()
    assert len(response.attachments) == 1
    await interface.ask_human('Is the above result *light*?')
    await interface.send_message('=theme dark')
    await interface.wait_for_message()
    await interface.send_message(r'=tex \text{This should be dark}')
    response = await interface.wait_for_message()
    assert len(response.attachments) == 1
    await interface.ask_human('Is the above result *dark*?')


@automata_test_human
async def test_latex_inline(interface):
    await interface.wait_for_reply('=set channel f-inline-tex enable')
    await interface.wait_for_reply('Testing $$x^2$$ Testing')
    await interface.ask_human('Does the above image say `Testing x^2 Testing`?')


# @automata_test_human
# async def test_latex_edit(interface):
#     command = await interface.send_message('=tex One')
#     result = await interface.wait_for_message()
#     await interface.ask_human('Does the above message have an image that says `One`?')
#     command = await interface.edit_message(command, '=tex Two')
#     await interface.wait_for_delete(result)
#     await interface.wait_for_message()
#     await interface.ask_human('Does the above message have an image that says `Two`?')


@automata_test
async def test_wolfram_simple(interface):
    await interface.send_message('=wolf hello')
    num_images = 0
    while True:
        result = await interface.wait_for_message()
        if result.content != '':
            break
        num_images += 1
    await interface.ensure_silence()
    assert num_images > 0


@automata_test
async def test_wolfram_pup_simple(interface):
    await interface.send_message('=pup solve (x + 3)(2x - 5)')
    assert (await interface.wait_for_message()).content == ''
    assert (await interface.wait_for_message()).content != ''
    await interface.ensure_silence()


@automata_test
async def test_wolfram_no_data(interface):
    await interface.send_message('=wolf cos(x^x) = sin(y^y)')
    result = await interface.wait_for_message()
    assert result.content != ''
    await interface.ensure_silence()


@automata_test
async def test_error_throw(interface):
    await interface.assert_reply_contains('=throw', 'Something went wrong')


@automata_test
async def test_calc5_storage(interface):
    await interface.wait_for_reply('=calc x = 3')
    await interface.assert_reply_equals('=calc x ^ x', '27')


@automata_test
async def test_calc5_timeout(interface):
    await interface.wait_for_reply(
        '=calc f = (x, h) -> if (h - 40, f(x * 2, h + 1) + f(x * 2 + 1, h + 1), 0)')
    await interface.assert_reply_equals('=calc f(1, 1)', 'Calculation took too long')


@automata_test
async def test_calc5_token_failure(interface):
    await interface.assert_reply_contains('=calc 4 @ 5', 'Invalid token at position 2')


@automata_test
async def test_calc5_syntax_failure(interface):
    await interface.assert_reply_contains('=calc 4 + 6 -', 'Invalid syntax at position 7')
