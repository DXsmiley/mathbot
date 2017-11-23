# Abstract Syntax Tree Reference

The AST is made of a number of dictionaries. Each one has a `#` key specifying what type of object it is.

## `number` (numeric constant)
- `string`: A string containing the number.

## `bin_op` (binary operator)

- `left`: AST of the left-hand operand.
- `right` AST of the right-hand operand.
- `operator`: String containing the operator symbol.

## `not` (unary not operator)

- `expression`: AST of the value.

## `die` (dice rolling operator)

- `times`: Optional AST of the number of dice to roll. If not specified, only one die should be rolled.
- `faces`: AST of the number of faces on each dice.

## `uminus` (unary minus operator)

- `value`: AST of the value.

## `function_call` (when a function is actually called)

This does not differentiate between macros and normal functions.

- `function`: AST of the expression used to get the function object.
- `augments`: Dictionary with the key `items` containing a list of ASTs.

## `word` (a variable name)

- `string`: name of variable

## `factorial` (unary operator)

- `value`: AST

## `assignment` (statement)

- `variable`:  A `word`.
- `value`: AST.

## `statement_list` (this is effectively a program)

- `statement`: AST of a statement.
- `next`: Either None, or a `statement_list`.

## `program` (DEPRECATED?)

- `items`: List of statements?

## `function_definition`

- `parameters`: Dictionary with key `items` being a list of `word`s
- `kind`: Either the string `"->"` or `"~>"` depending if it's a normal function or a macro function.
- `variadic`: Whether the last parameter is variadic or not.
- `expression`: The body of the function.

## `comparison`

- `first`: Leftmost thing, AST.
- `rest`: List of comparison blobs.

### blob

- `operator`: The comparison operator. Sits to the left of the value.
- `value`: An AST.

## `output` (deprecated)

- `expression`: AST.
