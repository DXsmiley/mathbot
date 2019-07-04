:::topics history calchistory calc-history

# Calculator History

**This feature is still in development**

By default, the calculator's memory (for assigned values, defined functions) is *at most* 24 hours, and resets whenever the bot restarts.

However, on servers *owned by Patrons* or in DMs *with Patrons*, the bot will remember values and functions for a much longer period of time.

To check the status of the calculator's history, run `=calc-history`. Remember that only commands which changed the *state* of the calculator are remembered. Simple commands such as `1 + 3` or `sin(4)` are not retained.

## Memory Clearance

Even with history enabled, the bot will clear it's memory *for a particuar channel* if the calc command has not been invoked in that channel for a bit over a week.

Commands that result in an error are not stored in the history.

Commands that result in an error during re-run are removed from the history.

## Patronage

Become a Patron and support the bot: https://www.patreon.com/dxsmiley

You must subscribe to the quadratic tier or higher to get access to the calculator history.