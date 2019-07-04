:::topics turing

# Turing Completeness

See `{{prefix}}help calc-more` for a list of basic builtin functions. See `{{prefix}}help turing-library` for builtin functions that operate over more complicated data structures.

## Introduction

The calculator is actually Turing complete, and can function as it's own small programming language, allowing you to perform more complicated operations.

Note that these features are currently in *beta* and may be unstable. More complete documentation will be coming later.

- Any variables that are assigned are contained to the channel that they are created in.
- Values are purged at least once every 24 hours, so don't rely on the bot to store important information for you.

## A note on commas

Commas are used in most programming languages to separate expressions, for example in lists of arguments. In the MathBot calculator, expressions are *mostly* optional, however may have to be used in some situations in order to prevent the parser joining adjacent expressions.

For example `[x y z]` is the same as `[x, y, z]`. `[x y (z)]` is *not* the same as `[x, y, (z)]`. In the first case, `y(z)` is interpreted as a function call. Adding the comma prevents this from happening.

Adding additional commas is a bad idea and will probably result in parsing errors.

:::page-break

## Language Features

### Assignments

Assigning variables is simple:

    x = 7
    

Recalling them works the same as it normally would

    x
    

### If Statements

If statements are use as follows:

    if (condition, expression_if_true, expression_if_false)
    

So for instance `if(1 < 2, 3, 4)` would evaluate to `3`, but `if(1 > 2, 3, 4)` would evaluate to `4`.

Unlike normal functions, the arguments that are passed to the `if` statement are only evaluated when they are used internally, not beforehand. This means that only one of `expression_if_true` and `expression_if_false` will ever be evaluated.

Additional arguments can be passed in order to make the function act as an if-elif-else block.

    ifelse(cond_1, expr_1,
        cond_2, expr_2,
        cond_3, expr_3,
        otherwise
    )
    

Which is the same as

    if (cond_1, expr_1,
        if (cond_2, expr_2,
            if (cond_3, expr_3,
                otherwise
            )
        )
    )
    

:::page-break

### Defining Functions

Anonymous functions are defined using the following syntax

    (arg1 arg2 arg3 ...) -> expression
    

Example:

    (x y z) -> (x * y) / z
    

These can then be assigned to variables

    double = (x) -> x * 2
    

Alternatively, functions defined at the top level can be given names.

    add(x y) = x + y
    

Anonymous functions that take a single argument can be defined using a shorthand that excludes the parenthesis.

    a -> a + 1
    

### Macro Functions

*Macros may be removed at some point in the future, since they serve no purpose in a lazy language.*

Macros are similar to normal functions, with the difference that all arguments have to be evaluated on demand: Your function gets a series of functions, which take no arguments and return the original value.

Macros are defined using the following syntax.

    (arg1 arg2 arg3 ...) ~> expression
    

Note the use of `~>` instead of `->`.

For example, the following snippet will evaluate to `8`

    sum_macro(x, y) ~> x() + y()
    sum_macro(3, 5)
    

:::page-break

### Lists

"Lists" are data structures that act like stacks: you can quickly access the head of a list, adding and removing things from it as required. You can access things further down a list but it'll be slower.

Lists are defined with square braces: `[1 2 3 4]`. The empty list is declared with `[]`.

The `:` operator inserts an item at the head of a list.

    1:[2 3 4] # Results in [1 2 3 4]
    

The `'` operator retrieves an item from the head of a list. If the list is empty, an error occurs.

    '[1 2 3 4] # Results in 1
    

The `` operator retrieves the tail of the list, i.e. all elements except the first. If the list is empty, an error occurs.

    \[1 2 3 4] # Results in [2 3 4]
    

### Text

"Strings" are defined as lists of "glyphs", where a glyph is a single character (like the letter `a`, digit `7`, or the poop emoji). String are denoted with double-quotes: "Hello, world!". Glyphs are denoted with the `;` character followed by the glyph itself.

Appending a glyph to the start of a string (the brakets aren't required here)

    (;h):("ello")
    

Note that `;` is represents a single space.

:::page-break

### Assoc-Lists

"Assoc-Lists" are a data structure similar to dictionaries. That means you can associate certain keys to certain values. For instance i could create a dictionary that says certain books refer to certain authors.

Assoc-Lists are implemented as lists, and they consist of a list of pairs: `[["a" 1] ["b" 2] ["c" 3]]` would be an assoc list mapping.

    "a" -> 1
    "b" -> 2
    "c" -> 3
    

You can add more key-value pairs to the list using the `assoc` function: `assoc([["a" 1] ["b" 2] ["c" 3]] "hello" 55)` would result in the assoc-list `[["a" 1] ["b" 2] ["c" 3] ["hello" 55]]`. One key can only be mapped to one element, for instance you can't get `[["a" 1] ["a" 2] ["b" 3]]`.

You can get a value given a key by using the function `get`: `get([["a" 1] ["b" 2] ["c" 3] ["hello" 55]] "hello")` would return `55`.

You can remove a key with the function `aremove`: `aremove([["a" 1] ["b" 2] ["c" 3] ["hello" 55]] "b")` would return `[["a" 1] ["c" 3] ["hello" 55]]`.

### Sets

Sets are lists where every element is unique, in order to make a set simply use the function `to_set`. As an example: `to_set([2,1,5,2,3,5,1])` would return `[3,1,5,2]`. Note that order isn't preserved, for instance `to_set([1,2,3,4])` gives `[1, 3, 4, 2]`.

Adding an element to the set is done with `set_insert`: `set_insert([1,2,3,4], 2)` becomes `[4,3,2,1]`.

:::page-break

# Memoisation

User-defined non-macro functions have memoisation applied to them automatically.

Thus, the following code executes quickly, even for large `x`:

    fib(x) -> if (x < 2, 1, fib(x - 2) + fib(x - 1))
    

The memoisation is not foolproof and could probably do with some improvement.

# Tail recursion optimisation

Simple situations for tail-recursion are optimised in order to conserve stack frames.

For example, the standard library defines the `reverse` function as the following:

    _reverse(input output) -> if(!input output _reverse(\input 'inputs:output))
    reverse(list) -> _reverse(input .)
    

Which works by repeatedly taking the top item from the input list and perpending it to the output list.