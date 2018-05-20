:::topics libraries lib libs libs-add libs-remove libs-list

# Calculator Libraries

**This feature is still in development**

The mathbot calculator supports loading of custom libraries. Libraries can be used to specify new functions and values.

Libraries are set up on a per-server basis, and are applied to all channels in that server. Libraries cannot be added to private chats with the bot.

## List libraries: `libs-list`

Lists all libraries in the current server.

## Add a new library: `libs-add url`

Add a new library at the given `url` to the current server.

`url` should be the url of a gist, such as this one: <https://gist.github.com/DXsmiley/a99cdce813e49a3a4f027bfce38865bc>

## Remove a library: `libs-remove url`

Remove the library at the given `url` from the current server.

## Writing libraries.

Writing libraries is quite simple. Create a gist at <https://gist.github.com> and add two files to it: `readme.md` containing documentation, and `source`, containing the code itself.

See this gist for an example: <https://gist.github.com/DXsmiley/a99cdce813e49a3a4f027bfce38865bc>
