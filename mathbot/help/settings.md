:::topics setting set settings options option setup permissions

# Settings

MathBot has a number of settings that can be changed in order to modify its behaviour.

Most notably, server admins are able to enable or disable certain commands on their own servers, on a per-channel basis.

There are also settings for customising command output.

## Command Description

The general structure of the settings command is:

```
{{prefix}}set context setting value
```

`context` should be one of the following:

- `server` - to apply the setting to the current server
- `channel` - to apply the setting to the current channel
- `self` - to apply the setting to yourself

`setting` should be the name of one of the settings, listed below.

`value` should be a valid value for the setting. See below for details.

:::page-break

## Permission Settings

These settings can be applied to the `server` and `channel` contexts, but only by server admins.

`value` should be either `enable`, `disable`, or `original`. `enable` will allow people to use the command in the given context and `disable` will stop people from using it. `original` will reset the value to the default. Note that if both a server-wide option and a channel-specific option apply to a specific channel, setting the channel to `original` will mean that it defers to the setting used by the server.

- `c-tex` : Enable or disable the `{{prefix}}tex` command. Default: Enabled
- `c-calc` : Enable or disable the `{{prefix}}calc` command. Default: Enabled
- `c-wolf` : Enable or disable the `{{prefix}}wolf` command. Default: Enabled
- `f-calc-shortcut` : Enable or disable the `==` shortcut for the `{{prefix}}calc` command. Disabling this **will not** produce an error message if a user attempts to use this command. This is intended to be used *only* if this command conflicts with other bots on your server. Default: Enabled
- `f-wolf-filter`: Enable or disable the word filter for W|A queries. This is enabled by default for all non-nsfw channels.
- `f-inline-tex`: Enable or disable the ability to add inline tex to messages. See `=help tex` for details. Default: **Disabled**.

## Examples

Disable the `=wolf` command on a server:
`{{prefix}}set server c-wolf disable`

Enable the `=calc` command on a single channel:
`{{prefix}}set channel c-calc enable`

## Troubleshooting

Ensure you are typing words *exactly* as shown.
:::discord
If you are still having problems you can ask on the official server: {{server_link}}
:::endblock
:::webpage
If you are still having problems you can ask [on the official server]({{server_link}}).
:::endblock
