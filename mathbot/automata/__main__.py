import automata
import core.parameters


auto = automata.Automata()


@auto.test()
async def sample(interface):
	assert True


@auto.test()
async def addition(interface):
	await interface.send_message('=calc 2+2')
	response = await interface.wait_for_message()
	assert response.content == '4'


@auto.test()
async def calc_shortcut(interface):
	await interface.send_message('== 8 * 9')
	response = await interface.wait_for_message()
	assert response.content == '72'


@auto.test()
async def calc_settings(interface):
	await interface.assert_reply_equals('== 2*3', '6')
	await interface.assert_reply_contains('=set channel f-calc-shortcut disable', 'applied')
	await interface.send_message('== 5-3')
	await interface.ensure_silence()
	await interface.assert_reply_contains('=set channel f-calc-shortcut original', 'applied')
	await interface.assert_reply_equals('== 8/2', '4')


@auto.test()
async def permissions(interface):
	E = 'That command may not be used in this location.'
	await interface.assert_reply_contains('=set channel c-calc original', 'applied')
	await interface.assert_reply_contains('=set server c-calc original', 'applied')
	await interface.assert_reply_equals('=calc 1+1', '2')
	await interface.assert_reply_contains('=set channel c-calc disable', 'applied')
	await interface.assert_reply_equals('=calc 1+1', E)
	await interface.assert_reply_contains('=set server c-calc disable', 'applied')
	await interface.assert_reply_equals('=calc 1+1', E)
	await interface.assert_reply_contains('=set channel c-calc enable', 'applied')
	await interface.assert_reply_equals('=calc 1+1', '2')
	await interface.assert_reply_contains('=set channel c-calc original', 'applied')
	await interface.assert_reply_equals('=calc 1+1', E)
	await interface.assert_reply_contains('=set server c-calc original', 'applied')
	await interface.assert_reply_equals('=calc 1+1', '2')


@auto.test()
async def latex(interface):
	await interface.send_message('=tex Hello')
	response = await interface.wait_for_message()
	assert len(response.attachments) == 1


@auto.test(needs_human = True)
async def latex_settings(interface):
	await interface.send_message('=set self p-tex-colour light')
	await interface.wait_for_message()
	await interface.send_message(r'=tex \text{This should be light}')
	response = await interface.wait_for_message()
	assert len(response.attachments) == 1
	await interface.ask_human('Is the above result *light*?')
	await interface.send_message('=set self p-tex-colour dark')
	await interface.wait_for_message()
	await interface.send_message(r'=tex \text{This should be dark}')
	response = await interface.wait_for_message()
	assert len(response.attachments) == 1
	await interface.ask_human('Is the above result *dark*?')


@auto.test()
async def latex_edit(interface):
	command = await interface.send_message('=tex One')
	result = await interface.wait_for_message()
	command = await interface.edit_message(command, '=tex Two')
	await interface.wait_for_delete(result)
	await interface.wait_for_message()


@auto.test()
async def wolfram_simple(interface):
	await interface.send_message('=wolf hello')
	num_images = 0
	while True:
		result = await interface.wait_for_message()
		if result.content != '':
			break
		num_images += 1
	await interface.ensure_silence()
	assert num_images > 0


@auto.test()
async def wolfram_no_data(interface):
	await interface.send_message('=wolf cos(x^x) = sin(y^y)')
	result = await interface.wait_for_message()
	assert result.content != ''
	await interface.ensure_silence()


@auto.test()
async def error_throw(interface):
	await interface.send_message('=throw')
	await interface.wait_for_failure()


@auto.test()
async def calc5_storage(interface):
	await interface.wait_for_reply('=calc x = 3')
	await interface.assert_reply_equals('=calc x ^ x', '27')


@auto.test()
async def calc5_timeout(interface):
	await interface.wait_for_reply('=calc f = (x, h) -> if (h - 40, f(x * 2, h + 1) + f(x * 2 + 1, h + 1), 0)')
	await interface.assert_reply_equals('=calc f(1, 1)', 'Calculation took too long')


@auto.test()
async def calc5_token_failure(interface):
	await interface.assert_reply_contains('=calc 4 & 5', 'unexpected symbol')


@auto.test()
async def calc5_syntax_failure(interface):
	await interface.assert_reply_contains('=calc 4 + 6 -', 'invalid syntax')


auto.run(
	core.parameters.get('automata token'),
	core.parameters.get('automata target')
)
