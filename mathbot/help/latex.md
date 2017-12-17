:::topics latex tex rtex

# LaTeX

The `{{prefix}}tex` command is used render *LaTeX* equations.

The *LaTeX* rendering is done by <http://rtex.probablyaweb.site/>

You can use the `{{prefix}}theme` command to change the colour of the results.

## Examples

`{{prefix}}tex x = 7`

`{{prefix}}tex \sqrt{a^2 + b^2} = c`

`{{prefix}}tex \int_0^{2\pi} \sin{(4\theta)} \mathrm{d}\theta`

## Limitations

The bot currently uses an external rendering service. The following features are known to break things:

 - `$` to start and end the equations. These are not required, and may do strange things. Use `\text{words}` to place text.
 - `\usepackage`, for any reason.
 - Macros such as `\@ifpackageloaded`.
 - Loading of external images, and other resources.

## Inline LaTeX

*This feature is currently disabled by default and must be turned on by the server owner. The server owner should run the command `=set server f-inline-tex enable`.*

You can insert LaTeX into the middle of a message by wrapping it in `$$` signs.

Examples

`The answer is $$x^{2 + y}$$.`

`$$1 + 2$$ equals $$3$$.`

## Deleting Commands

You can get the bot to automatically delete invokation commands after a short time by setting `=set server f-delete-tex enable`.
The bot will require the *manage messages* permission for this work properly.

## Custom Macros

Some custom commands have been added to make typing quick LaTeX easy. These include `\bbR`, `\bbN` etc. for `\mathbb{R}`, `mathbb{N}` and other common set symbols and `\bigO` for `\mathcal{O}`. Some unicode characters (such as greek letters) are automatically convered to LaTeX macros for ease of use.
