:::topics setting set settings options option setup permissions

# Settings

MathBot has a number of settings that can be changed in order to modify its behaviour.

Server admins are able to enable or disable certain commands on their own servers, on a per-channel basis.

There are also settings for customising command output.

## Command Description

The general structure of the settings command is:

```
{{prefix}}set context setting value
```

`context` should be either `channel` or `server`.
`setting` should be the name of one of the settings, listed below.
`value` should be a valid value for the setting. Either `enable`, `disable` or `reset`.

:::page-break

## Permission Settings

These settings can be applied to the `server` and `channel` contexts, but only by server admins.

`value` should be either `enable`, `disable`, or `reset`. `enable` will allow people to use the command in the given context and `disable` will stop people from using it. `reset` will reset the value to the default. Note that if both a server-wide option and a channel-specific option apply to a specific channel, setting the channel to `reset` will mean that it defers to the setting used by the server.

- `c-calc` : Toggles the `{{prefix}}calc` command. Default: *Enabled*
- `c-tex` : Toggles the `{{prefix}}tex` command. Default: *Enabled*
- `c-wolf` : Toggles the `{{prefix}}wolf` command. Default: *Enabled*
- `f-calc-shortcut` : Toggles the `==` shortcut for the `{{prefix}}calc` command. Disabling this **will not** produce an error message if a user attempts to use this command. This is intended to be used *only* if this command conflicts with other bots on your server. Default: *Enabled*
- `f-tex-inline`: Toggles the ability to add inline tex to messages. See `=help tex` for details. Default: *Disabled*.
- `f-tex-delete`: When enabled, the bot will delete messages used to invoke the tex command after a few seconds. Default: *Disabled*.
- `f-wolf-filter`: Toggles the word filter for W|A queries. This is enabled by default for all non-nsfw channels.
- `f-wolf-mention`: Toggles the `@mention` in the footer of W|A results. Default: *Enabled*.
- `m-disabled-cmd`: Toggles the "That command cannot be used in this location" message. Default: *Enabled*.

:::page-break

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

## Extra tools

To check which settings apply to a particular channel, run the `{{prefix}}checkallsettings` command in that channel.
