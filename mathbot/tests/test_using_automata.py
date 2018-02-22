''' Test the bot by running an instance of it and interfacing
    with it through Discord itself.
'''

# pylint: disable=missing-docstring

from conftest import automata_test, automata_test_human

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
async def test_supress_permission_warning(interface):
    err = 'That command may not be used in this location.'
    await interface.assert_reply_equals('=calc 1+1', '2')
    await interface.assert_reply_contains('=set channel c-calc disable', 'applied')
    await interface.assert_reply_contains('=calc 1+1', err)
    await interface.assert_reply_contains('=set channel m-disabled-cmd disable', 'applied')
    await interface.send_message('=calc 1+1')
    await interface.ensure_silence()
    await interface.assert_reply_contains('=set channel c-calc original', 'applied')
    await interface.assert_reply_contains('=set channel m-disabled-cmd original', 'applied')


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


@automata_test
async def test_dice_rolling(interface):
    for i in ['', 'x', '1 2 3', '3d']:
        await interface.assert_reply_contains('=roll ' + i, 'Format your rolls like')
    for i in ['1000000', '100001', '800000 d 1', '500000 500000']:
        message = await interface.wait_for_reply('=roll ' + i)
        assert 'went wrong' not in message.content
    for i in ['6', 'd6', '1d6', '1 6', '1 d 6']:
        message = await interface.wait_for_reply('=roll ' + i)
        assert int(message.content[2]) in range(1, 7)
