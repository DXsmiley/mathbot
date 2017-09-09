:::topics calculator calc

# Calculator

The calculator can be invoked with the command `{{prefix}}calc`.

It is also possible to use the shortcut `==`, however *this may be disabled on some servers or channels*. Using the shortcut will not produce an error message if it is disabled.

To see details on the calculator's Turing completeness, run `{{prefix}}help turing`.

The calculator supports the following arithmetic operations:

    - `+` : addition
    - `-` : subtraction
    - `*` : multiplication (can also use `×`)
    - `/` : division (can also use `÷`)
    - `^` : exponentiation (has some limitations to prevent exploits)
    - `!` : factorial (cannot be applied to numbers greater than 200)

The following comparisons are supported

    - `>` : Greater than.
    - `<` : Less than.
    - `==` : Equal to (two `=` signs for comparison)
    - `>=` : Greater or equal.
    - `<=` : Less than or equal.
    - `!=` : Not equal.

For example, `2 < 5 < 8` evaluates to `True`, whereas `3 == 6` equates to `False`.

The following logical operators are supported:

    - `|` : Or  (`x | y`)
    - `&` : And (`x & y`)
    - `!` : Not (`!x`)

The value `0` is considered falsy. Everything else is truthy.

The following constants exist:

    - `pi`  : 3.141592... (also `π`)
    - `tau` : 6.283185... (twice pi)
    - `e`   : 2.178281...
    - `true`  : 1
    - `false` : 0

:::page-break

The following functions are available:

    - `sin(x)` : sine of an angle (radians)
    - `cos(x)` : cosine of an angle (radians)
    - `tan(x)` : tan of an angle (radians)
    - `sind(x)` : sine of an angle (degrees)
    - `cosd(x)` : cosine of an angle (degrees)
    - `tand(x)` : tan of an angle (degrees)
    - `asin(x)` : inverse sine (radians)
    - `acos(x)` : inverse cosine (radians)
    - `atan(x)` : inverse tan (radians)
    - `asind(x)` : inverse sine (degrees)
    - `acosd(x)` : inverse cosine (degrees)
    - `atand(x)` : inverse tan (degrees)
    - `sinh(x)` : hyperbolic sine function
    - `cosh(x)` : hyperbolic cosine function
    - `tanh(x)` : hyperbolic tan function
    - `asinh(x)` : inverse hyperbolic sine
    - `acosh(x)` : inverse hyperbolic cosine
    - `atanh(x)` : inverse hyperbolic tan
    - `deg(r)` : converts radians to degrees
    - `rad(d)` : converts degrees to radians
    - `log(x)` : log in base 10
    - `log(x, b)` : log of `x` in base `b`
    - `ln(x)`  : log in base `e`
    - `sqrt(x)` : calculates the square root of a number
    - `round(x)` : rounds a number to the nearest integer
    - `int(x)` : rounds *down* to the nearest integer
    - `gamma(x)` : computes the gamma function
    - `gcd(a, b)` : computes the greatest common denominator or a and b
    - `lcm(a, b)` : computes the lowest common multiple of a and b
    - `choose(n, k)` : computes `n` choose `k`

:::page-break

You can use the following notation to roll dice:

    - `dX` : rolls an `X`-sided die. (e.g. `d20`)
    - `YdX` : rolls `Y` `X`-sided dice. (e.g. `2d6`) and gives the total.

You cannot roll more than 1000 dice at once.

Appending the equation with `: R`, where `R` is an integer will repeat
the calculation that many times. Useful only if you want to roll many
dice at once. Using the `{{prefix}}csort` or `{{prefix}}sort` command will sort the numbers
in increasing order. `R` may not be greater than 50.

## Examples

`{{prefix}}calc 2 ^ (1 + 3) * 5`

`{{prefix}}calc round(10 / 3)`

`{{prefix}}calc sin(pi / 2)`

`{{prefix}}calc 8d6 : 10`
