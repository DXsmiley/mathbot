# Bytecode Reference

- 0 - Nothing
- 1 - Constant [value]
- 2 - Binary Addition
- 3 - Binary Subtraction
- 4 - Binary Multiplication
- 5 - Binary Division
- 6 - Binary Subtraction
- 7 - Binary Power
- 8 - Binary Logical And
- 9 - Binary Logical Or
- 10 - Binary Die roll
- 11 - Unary Not
- 12 - ???
- 13 - Unary Factorial
- 14 - Jump is macro [destination]
- 15 - Argument list end [number of arguments, jump macro, jump end]
- 16 - Word (variable access)
- 17 - Assignment [value]
- 18 - Swap top two items of the stack
- 19 - End program
- 20 - Declare macro function
- 21 - Declare normal function
- 22 - Return from function
- 23 - Jump [address]
- 24 - Jump if true [addres]
- 25 - Jump if false [address]
- 26 - Duplicate top value
- 27 - Discord top value from stack

- 28 to 34 - Binary comparators
- 25 to 40 - Comparators used for chains

- 41 - Store in cache
- 42 - Demacroify
- 43 - Store-demacrod - Demacro'd function


## Chain comparators

Do the following:

pop and store in R
pop and store in L
push L (compare) R
logical and with top item on stack
push R to stack


# Functions

## Function call bytecode

(function is placed on the stack)
(functions to access arguments are placed on stack)
(integer zero is placed on the stack)
DEMACROIFY
: number of arguments
STORE_DEMACROD
ARG_LIST_END
: number of arguments
STORE_IN_CACHE

Note: macro functions do not have their results cached because the functions that get passed into them are newly created every time, making it uncacheable.

## Entering a function

if results are going to be cached:
	push function object
	push cache key
push return address
push return scope
goto function bytecode

After the `RETURN` function is executed, the stack will no longer have the address and scope. Instead it will have the result of the function. The `STORE_IN_CACHE` instruction then has to be called in order to remember the result.

## Function definition

### Creating a function object

FUNCTION_MACRO or FUNCTION_NORMAL
start_address

### Function definiton in the byte code

:start_address (be aware that this takes up a byte)
number of parameters
(parameter names here)
1 if variadic, 0 otherwise
(expression)
RETURN


# Specials

## Map

:push function to stack
:push array to stack
:push empty array to stack
Run map instruction repeatedly

## Reduce

:push function to stack
:push array to stack
:push first element of array to stack
:push number one to stack
Run reduce instruction repeatedly

SPECIAL_REDUCE
STORE_IN_CACHE
SPECIAL_REDUCE_STORE