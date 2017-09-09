:::topics wolfram wolf wolframalpha wolfram|alpha wa alpha

# Wolfram|Alpha

The `{{prefix}}wolf` command is used to query Wolfram|Alpha.

This command can be very slow at times, so please be patient.

You can use the `{{prefix}}theme` command to change the colour of the results.

## Examples

`{{prefix}}wolf intersection of sin(x) and cos(x)`

`{{prefix}}wolf x^3 - x^2 + x - 1`

## Refining your results

This command will give you *all* the information that Wolfram|Alpha spits out, which is often more than you want. It understand some english, so you can use words to refine your query. For example, you might use `roots of x^2 - x - 1` rather than `y = x^2 - x - 1` if you only want the solutions to the equation.

## Assumptions

Sometimes Wolfram|Alpha will make some assumptions about your intentions. These will be displayed at the bottom of the message. If you wish to change what W|A assumes, you can click on the letter reactions (🇦, 🇧, etc...), and then click the 🔄 reaction to re-run the query.

## Query Filters

To avoid people abusing the bot, some queries will not be run. The filter applies to all channels except for direct messages and channels marked as nsfw.

A server admin can be manually disable the filter in a channel by running `{{prefix}}set channel f-wolf-filter disable`.
It can be re-enabled again with `{{prefix}}set channel f-wolf-filter enable`.

See `{{prefix}}help settings` for more details on managing settings.
