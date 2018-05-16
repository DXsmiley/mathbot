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

ERROR_MESSAGE_TOO_LONG = """\
Something went wrong while handling a long messge.
If this error keeps recurring, you should report it to DXsmiley on the \
official MathBot server: https://discord.gg/JbJbRZS
"""

ERROR_MESSAGE_EXTRA = """\
**(Shard {})** Something went wrong while handling the message:
```
{}
```

Details:
```
{}
```

"""

ERROR_MESSAGE_CUSTOM = """
**(Shard {})** Custom error report:
{}
"""

async def send(client, origin, query, extra = ''):
	''' Send details of an error to the channel which
		triggered it. Also send extra details to a specific
		channel which can be used to log the bot.
	'''
	channel_id = core.parameters.get('error-reporting channel')
	# Error message to user immidiately
	query_clean = query.replace('```', '\`\`\`')
	message = ERROR_MESSAGE_EXCEPTION.format(query_clean)
	if len(message) > 2000:
		message = ERROR_MESSAGE_TOO_LONG
	await client.send_message(origin, message)
	# Send details to official error place
	if len(extra) > 1500:
		extra = '... ' + extra[-1500:]
	message = ERROR_MESSAGE_EXTRA.format(client.shard_id, query_clean, extra)
	modules.reporter.enque(message)


async def custom_report(client, message):
	''' Sends text to the error logging channel.
		Can be used for any custom reason.
	'''
	m = ERROR_MESSAGE_CUSTOM.format(client.shard_id, message)
	modules.reporter.enque(m)
