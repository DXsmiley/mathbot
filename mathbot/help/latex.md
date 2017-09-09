:::topics latex tex rtex

# LaTeX

The `{{prefix}}tex` command is used render *LaTeX* equations.

The *LaTeX* rendering is done by <http://quicklatex.com/>

You can use the `{{prefix}}theme` command to change the colour of the results.

## Example

`{{prefix}}tex x = 7`

`{{prefix}}tex \sqrt{a^2 + b^2} = c`

`{{prefix}}tex \int_0^{2\pi} \sin{(4\theta)} \mathrm{d}\theta`

## Limitations

The bot currently uses an external rendering service. The following features are known to break things:

 - `$` to start and end the equations. These are not required, and may do strange things. Use `\text{words}` to place text.
 - `\usepackage`, for any reason.
 - Macros such as `\@ifpackageloaded`.
 - Loading of external images, and other resources.
