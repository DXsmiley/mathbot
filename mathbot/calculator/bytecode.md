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


## Chain comparators

Do the following:

pop and store in R
pop and store in L
push L (compare) R
logical and with top item on stack
push R to stack