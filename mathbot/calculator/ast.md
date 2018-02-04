# Abstract Syntax Tree Reference

The AST is made of a number of dictionaries. Each one has a `#` key specifying what type of object it is.

## `number` (numeric constant)

- `string`: A string containing the number.

## `bin_op` (binary operator)

- `left`: AST of the left-hand operand.
- `right` AST of the right-hand operand.
- `operator`: String containing the operator symbol.
- `token`: Token of the operator.

## `percent_op` (unary percentage operator)

- `token`: Token of the operator.
- `value`: AST of a `number`.

## `not` (unary ! operator)

- `expression`: AST of the value.
- `token`: Token of the operator.

## `uminus` (unary minus operator)

- `value`: AST of the value.

## `head_op` (get head of list, unary operator ')

- `token`: Token of the ' operator
- `expression`: AST of the thing to get the head of.

## `tail_op` (get tail of the list, unqry operator \)

- `token`: Token of the \ operator
- `expression`: AST of the thing to get the tail of.

## `function_call` (when a function is actually called)

This does not differentiate between macros and normal functions.

- `function`: AST of the expression used to get the function object.
- `augments`: Dictionary
	- `items`: List of the arguments
	- `edges`: Dictionary
		- `start`: The '(' token at the beginning of the argument list.
		- `end`: The ')' token at the end of the argument list.

## `word` (a variable name)

- `string`: name of variable

## `list_literal` [1 2 3]

- `items`: AST of the elements of the list

## `factorial` (unary operator)

- `value`: AST
- `token`: Token of the ! operator

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

# Error info

Error info can appear on (almost) any node. It specifies what section of the original source code to blame if something goes wrong, and can usually be found as node\['token'\]\['source'\].

Blame information looks like this:

{
	'name': 'source_filename.c5',
	'location': 10,
	'code': 'Original source code'
}
