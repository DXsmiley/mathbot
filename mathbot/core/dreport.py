import core.parameters
import traceback

ERROR_MESSAGE_EXCEPTION = """\
Something went wrong while handling the message:
```
{}
```

If this error keeps recurring, you should report it to DXsmiley on the \
official MathBot server: https://discord.gg/JbJbRZS
"""

ERROR_MESSAGE_EXTRA = """\
Something went wrong while handling the message:
```
{}
```

Details:
```
{}
```
"""

async def send(client, origin, query, extra = ''):
	''' Send details of an error to the channel which
		triggered it. Also send extra details to a specific
		channel which can be used to log the bot.
	'''
	channel_id = core.parameters.get('error-reporting channel')
	message = ERROR_MESSAGE_EXCEPTION.format(query)
	await client.send_message(origin, message)
	# Todo : need a better method of detecting release mode
	if channel_id and client.user.name == 'MathBot':
		try:
			message = ERROR_MESSAGE_EXTRA.format(query, extra)
			await client.send_message(client.get_channel(channel_id), message)
		except Exception as e:
			print('Issue when sending error message to official server')
			traceback.print_exc()
