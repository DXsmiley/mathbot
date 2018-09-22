:::topics calc-more

# Calculator

The calculator can be invoked with the command `{{prefix}}calc`.

It is also possible to use the shortcut `==`, however *this may be disabled on some servers or channels*. Using the shortcut will not produce an error message if it is disabled.

See `{{prefix}}help turing` for a list of extended features, such as function definition and list manipulation.
See `{{prefix}}help turing-library` for builtin functions that operate over more complicated data structures.

The calculator supports the following arithmetic operations:

    - `+` : addition
    - `-` : subtraction
    - `*` : multiplication (can also use `×`)
    - `/` : division (can also use `÷`)
    - `^` : exponentiation
    - `!` : factorial (e.g. `5!`)

The following comparisons are supported

    - `>` : Greater than.
    - `<` : Less than.
    - `==` : Equal to (two `=` signs for comparison)
    - `>=` : Greater or equal.
    - `<=` : Less than or equal.
    - `!=` : Not equal.

For example, `2 < 5 < 8` evaluates to `True`, whereas `3 == 6` equates to `False`.

The following logical operators are supported:

    - `||` : Or  (`x || y`)
    - `&&` : And (`x && y`)
    - `!` : Not (`!x`)

`false`, `0` and the empty list is considered falsy. Everything else is considered truthy.

The following constants exist:

    - `pi`  : 3.141592... (also `π`)
    - `tau` : 6.283185... (twice pi)
    - `e`   : 2.178281...
    - `true`  : 1
    - `false` : 0
    - `i` : The imaginary unit
    - `infinity` : representation of infinity
    - `complex_infinity` : infinity, but it's complicated
    - `not_a_number` : produced by some functions when given invalid input

:::page-break

The following functions are available:

```
|------------------------------------------------------------------|
| function | radians | degress | inverse radians | inverse degrees |
|------------------------------------------------------------------|
| Sine     | sin     | sind    | asin            | asind           |
| Cosine   | cos     | cosd    | acos            | acosd           |
| Tangent  | tan     | tand    | atan            | atand           |
| Cosecant | csc     | cscd    | acsc            | acscd           |
| Secant   | sec     | secd    | asec            | asecd           |
| Cotan    | cot     | cotd    | acot            | acotd           |
| Hyp-Sin  | sinh    |         | asinh           |                 |
| Hyp-Cos  | cosh    |         | acosh           |                 |
| Hyp-Tan  | tanh    |         | atanh           |                 |
|------------------------------------------------------------------|
```

:::page-break

    - `abs(x)` : the absolute value of x
    - `deg(r)` : converts radians to degrees
    - `rad(d)` : converts degrees to radians
    - `log(x)` : log in base 10
    - `log(x, b)` : log of `x` in base `b`
    - `ln(x)`  : natural logarithm `e`
    - `sqrt(x)` : calculates the square root of a number
    - `root(x, y)` : the `y`th root of `x`, equal to `x^(1/y)`
    - `ceiling(x)` : rounds a number *up* to the nearest integer
    - `floor(x)` : rounds *down* to the nearest integer
    - `exp(x)` : equivilent to e^x
    - `gamma(x)` : computes the gamma function
    - `factorial(x)` : computes the factorial function
    - `gcd(a, b)` : computes the greatest common denominator or a and b
    - `lcm(a, b)` : computes the lowest common multiple of a and b
    - `choose(n, k)` : computes `n` choose `k`
    - `re(x)` : extract the real part of a complex number
    - `im(x)` : extract the imaginary part of a complex number

:::page-break

## Examples

`{{prefix}}calc 2 ^ (1 + 3) * 5`

`{{prefix}}calc round(10 / 3)`

`{{prefix}}calc sin(pi / 2)`

`{{prefix}}calc (4 + 3i) ^ 3`
