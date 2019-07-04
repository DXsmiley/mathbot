:::topics blame

# Blame

The `{{prefix}}blame` command is used to find who caused the bot to post a certain message.

Usage: `{{prefix}}blame message_id` or `{{prefix}}blame recent`

The `message_id` should be the id of the message that the bot posted. You can find this by enabling developer tools, and then right-clicking on the message you wish to investigate. Using `recent` will get the blame for the most recent message that the bot posted in this channel.

The bot keeps message blames for only 50 hours. After this, blame records are removed to conserve space.