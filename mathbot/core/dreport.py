import core.parameters
import modules.reporter
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
	# Error message to user immidiately
	message = ERROR_MESSAGE_EXCEPTION.format(query)
	await client.send_message(origin, message)
	# Send details to official error place
	message = ERROR_MESSAGE_EXTRA.format(query, extra)
	modules.reporter.enque(message)


async def silent_report(client, message):
	''' Sends text to the error logging channel.
		Can be used for any custom reason.
	'''
	modules.reporter.enque(message)
