# MathBot

MathBot is a discord bot that contains a number of features to help with mathematics.

It's primary features are:
- LaTeX rendering
- Querying Wolfram|Alpha
- A Turing complete calculator

The bot is currently developed for python `3.6.4`.

## Links

- [Add the bot to your own server](https://discordapp.com/oauth2/authorize?&client_id=172236682245046272&scope=bot&permissions=126016)
- [Command documentation for users](https://dxsmiley.github.io/mathbot/docs.html)
- [Support me on Patreon](https://www.patreon.com/dxsmiley)
- [Project Trello Board](https://trello.com/b/j6b7vpGA/mathbot)
- [Official Discord Server](https://discord.gg/JbJbRZS)

## Setup for use

```bash
git clone https://github.com/DXsmiley/mathbot.git
cd mathbot
cp mathbot/parameters_default.json mathbot/parameters.json
pipenv --python 3.6
pipenv install --skip-lock
```

Then open parameters.json and change `tokens` to the token of the bot used for development. Optionally change the other parameters.

It is *strongly* recommend that you setup an instance of Redis if you want to use the bot on even a moderate scale. The disk-based keystore is easy to setup but runs very slowly, and as such is only useful of a development tool.

Then navigate into the `mathbot` directory and run the bot with `python bot.py parameters.json`.

## Setup for development

```bash
git clone https://github.com/DXsmiley/mathbot.git
cd mathbot
cp mathbot/parameters_default.json mathbot/parameters.json
pipenv --python 3.6
pipenv install --skip-lock
```

Then open parameters.json and change `tokens` to the token of the bot. Change `release` to `development`. Optionally change the other parameters.

Then navigate into the `mathbot` directory and run the bot with `python bot.py parameters.json`.

## Contributing guide

Relevent discussion takes place on [the MathBot Discord server](https://discord.gg/JbJbRZS).

For small changes, feel free to fork the repo and make a pull request once you've made the changes. For larger things, check the [Trello board](https://trello.com/b/j6b7vpGA/mathbot) and see if anyone's already working on it. If not, shoot me a message to say that you're working on it so we don't get multiple people doing the same thing.

Yes I use tabs for indentation.

## Setting up Wolfram|Alpha

1. [Grab yourself an API key](https://products.wolframalpha.com/api/)
2. Open parameters.json and change `wolfram > key`.

This should really only be used for development and personal use.

## Test Suite

Use the `test` script in side the `mathbot` folder to run the test suite.

Some of the tests require that a bot is running and connected to Discord. To enable them, use the `--run-automata` command line argument. In addition a file with the neccicary tokens filled out needs to be provided to the `--parameter-file` argument. To get all tests running, the *token*, *automata* and *wolfram* parameters need to be filled out.

For the sake example, I run my tests with the command `./test --run-automata --parameter-file=dev.json`. You should replace `dev.json` with a path to your own parameter file.

There are some additional tests that require a human to verify the bot's output. These can be enabled with `--run-automata-human`.

## Guide to `parameters.json`

- *release* : Release mode for the bot, one of `"development"`, `"beta"` or `"production"`
- *token* : Token to use for running the bot
- *wolfram*
	- *key* : API key for making Wolfram|Alpha queries
- *keystore*
	- *disk*
		- *filename* : The file to write read and write data to when in disk mode
	- *redis*
		- *url* : url used to access the redis server
		- *number* : the number of the database, should be a non-negative integer
	- *mode* : Either `"disk"` or `"redis"`, depending on which store you want to use. Disk mode is not recommended for deployment.
- *patrons* : list of patrons
	- Each *key* should be a Discord user ID.
	- Each *value* should be a string starting with one one of `"linear"`, `"quadratic"`, `"exponential"` or `"special"`. The string may contains additional information after this for human use, such as usernames or other notes.
- *analytics* : Keys used to post information to various bot listings.
	- *carbon*: Details for [carbonitex](http://carbonitex.net/)
	- *discord-bots*: API Key for [bots.discord.pw](https://bots.discord.pw/#g=1)
	- *bots-org*: API Key for [discordbots.org](https://discordbots.org/)
- *automata*
	- *token* : token to use for the automata bot
	- *target* : the username of the bot that the automata should target
	- *channel*: the ID of the channel that the tests should be run in
- *advertising*
	- *enable* : should be `true` or `false`. When `true`, the bot will occasionally mention the Patreon page when running queries.
	- *interval* : the number of queries between mentions of the Patreon page. This is measured on a per-channel basis.
	- *starting-amount* : Can be increased to lower the number of commands until the Patreon page is first mention.
- *error-reporting*
	- *channel*: ID of channel to send error reports to. If not specified, reports will not be sent.
- *shards*
	- *total*: The total number of shards that the bot is running on.
	- *mine*: A list of integers (starting at `0`) specifying which shards should be run in this process.
- *calculator*
	- *persistent*: `true` or `false`. Enable to remember calculator history between runs. Off by default.
	- *libraries*: `true` or `false`. Enables the `=libs` set of commands. Off by default.
