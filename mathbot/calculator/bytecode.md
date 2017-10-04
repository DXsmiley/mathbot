# Bytecode Reference

## Notation

- Words inside square brackets represent data stored in the bytecode directly after the insruction. For example `function [address]` represents that the `function` instruction should be followed by an address.
- Stack manipulation is listed in parenthesis. For example, the Binary Additional instructio coud be represented as `(a, b -> c)` representing that it pops the top two items from the stack and pushes a single item to the stack.

## List of Instructions

- 0 - Nothing

- 1 - Constant [value] ( -> t)
- 50 - Constant Empty Array ( -> empty_array)

- 2 - Binary Addition (a, b, -> c)
- 3 - Binary Subtraction (a, b, -> c)
- 4 - Binary Multiplication (a, b, -> c)
- 5 - Binary Division (a, b, -> c)
- 6 - Binary Modulo (a, b, -> c)
- 7 - Binary Power (a, b, -> c)
- 8 - Binary Logical And (a, b, -> c)
- 9 - Binary Logical Or (a, b, -> c)
- 10 - Binary Die roll (a, b, -> c)
- 11 - Unary Not (t -> t)
- 12 - Unary Minus (t -> t)
- 13 - Unary Factorial (t -> t)
- 14 - Jump if macro [destination] (f -> )
- 15 - Argument list end [number of arguments]
- 54 - Argument list end disable cache [number of arguments]
- 16 - Word (variable access) (DEAD)
- 17 - Assignment [address] (value -> )
- 18 - Swap top two items of the stack (a, b -> b, a)
- 19 - End program
- 20 - Declare macro function [address] ( -> f) (DEAD)
- 21 - Declare function [address] ( -> f)
- 22 - Return from function
- 23 - Jump [address]
- 24 - Jump if true [addres] (b -> )
- 25 - Jump if false [address] (b -> )
- 26 - Duplicate top value (a -> a, a)
- 27 - Discord top value from stack (a -> )

- 28 - Binary Comparison Less (l, r -> x)
- 29 - Binary Comparison More (l, r -> x)
- 30 - Binary Comparison Less Equal (l, r -> x)
- 31 - Binary Comparison More Equal (l, r -> x)
- 33 - Binary Comparison Equal (l, r -> x)
- 34 - Binary Comparison Not Equal (l, r -> x)
(where x = (l compare r))

- 35 - Chain Comparison Less (x, l, r -> y, r)
- 36 - Chain Comparison More (x, l, r -> y, r)
- 37 - Chain Comparison Less Equal (x, l, r -> y, r)
- 38 - Chain Comparison More Equal (x, l, r -> y, r)
- 39 - Chain Comparison Equal (x, l, r -> y, r)
- 40 - Chain Comparison Not Equal (x, l, r -> y, r)
(where y = x and (l compare r))

- 41 - Store in cache
- 42 - Demacroify (DEAD)
- 43 - Store-demacrod (demacro'd function) (DEAD)

- 44 - Access Global [index, variable name]
- 45 - Access Local  [index]
- 46 - Access Semi Local [index, depth]
- 53 - Access Array Element (array, index -> value)

- 48 - Special Map
- 51 - Special Map Store
- 49 - Special Reduce
- 52 - Special Reduce Store
- 55 - Special Filter
- 56 - Special Filter Store

## Chain comparators

To start a set of chain comparisons, the number 1 is pushed to the stack, followed by the first operand.

Each of the chain comparitor instructions do the following:
- pop form the stack and store in R
- pop form the stack and store in L
- pop from the stack and store in C
- push ((L compare R) and C) to the stack (logical and)
- push R to stack

To end a set of chain comparisons, the top item of the stack (which would be the very last R) is popped.

## Functions

### Function call bytecode

push the function to the stack
push the arguments to the stack (note that this might change depending on whether the function is a macro or not)
argument list end instruction [number of arguments]

### Entering a function

push return address
push return scope
If results are going to be cached, push cache key. 'NONE' can be pushed if the function has a `STORE_IN_CACHE` instruction but you want to prevent caching.
goto function bytecode

After the `RETURN` function is executed, the address and scope will be reset and the top of the stack will be the result of the function.

### Function definition

#### Creating a function object

`FUNCTION_NORMAL`
start_address

#### Function definiton in the byte code

 - start address (be aware that this takes up a byte, and it's empty)
- number of parameters
- 1 if variadic, 0 otherwise
- 1 if macro, 0 otherwise
- executable code starts here
- If not a macro: `STORE_IN_CACHE` insturction
- `RETURN` instruction

## Specials

### Map

:push function to stack
:push array to stack
:push empty array to stack
Run map instruction repeatedly

SPECIAL_MAP
SPECIAL_MAP_STORE

### Reduce

:push function to stack
:push array to stack
:push first element of array to stack
:push number one to stack
Run reduce instruction repeatedly

SPECIAL_REDUCE
SPECIAL_REDUCE_STORE

### Filter

:push function to stack (prediate)
:push array to stack (source)
:push empty array to stack (destination)
:push integer zero to the stack (iterator)
Run filter instruction repeatedly

SPECIAL_FILTER
SPECIAL_FILTER_STORE