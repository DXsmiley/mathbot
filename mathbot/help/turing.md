:::topics turing

# Turing Completeness

The calculator is actually Turing complete, and can function as it's own small programming language, allowing you to perform more complicated operations.

Note that these features are currently in *beta* and may be unstable. More complete documentation will be coming later.

 - Any variables that are assigned are contained to the channel that they are created in.
 - Values are purged at least once every 24 hours, so don't rely on the bot to store important information for you.

## Assignments

Assigning variables is simple:
```
x = 7
```

Recalling them works the same as it normally would
```
x
```

Note that the single-letter variable name **d** *cannot* be used, since it clashes with the die-rolling operator.

## If Statements

If statements are use as follows:
```
if(condition, expression_if_true, expression_if_false)
```

So for instance `if(1 < 2, 3, 4)` would evaluate to `3`, but `if(1 > 2, 3, 4)` would evaluate to `4`.

Unlike normal functions, the arguments that are passed to the `if` statement are only evaluated when they are used internally, not beforehand. This means that only one of `expression_if_true` and `expression_if_false` will ever be evaluated.

:::page-break

## Defining Functions

Functions are defined using the following syntax
```
(arguments, ...) -> expression
```

Example:
```
(x, y, z) -> (x * y) / z
```

Functions are not given names, but they can be assigned to variables so that they may be used later.
```
sum = (x, y) -> x + y
sum(3, 5)
```

## Macro Functions

Macros are similar to normal functions, with the difference that all arguments have to be evaluated on demand: Your function gets a series of functions, which take no arguments and return the original value.

Macros are defined using the following syntax:
```
(arguments, ...) ~> expression
```

For example, the following snippet will evaluate to `8`
```
sum = (x, y) ~> x() + y()
sum(3, 5)
```

## Combining the two

These tools are enough to create things such as the Fibonacci function:
```
fib = (n) -> if (n < 2, 1, fib(n - 2) + fib(n - 1))
```

## Additional inbuilt functions

There are also a number of additional inbuilt functions designed to help with building more complicated systems. There are described as follows:

    - `is_real(x)` - Determines whether x is a real number (an integer or a float).
    - `is_complex(x)` - Determines whether x is a complex number.
    - `is_function(x)` - Determines whether x is function (or a macro).
