# Grammar

```
superscript_number (regex) = [⁰¹²³⁴⁵⁶⁷⁸⁹]+
number (regex) = \d*\.?\d+([eE]-?\d+)?i?
word (regex) = π|[d][a-zA-Z_][a-zA-Z0-9_]*|[abce-zA-Z_][a-zA-Z0-9_]*

wrapped_expression = '(', expression, ')'

function_call = atom | function_call, '(', argument_list, ')'
logical_not = function_call | '!', logical_not
factorial = logical_not | factorial, '!'
dieroll = factorial | 'd', factorial | factorial, 'd', factorial
uminus = dieroll | '-', uminus
superscript = uminus, {superscript_number}

power = superscript | superscript, '^', power
modulo = [modulo, '%'], power
prod_op = '*', '/', '÷', '×'
product = [product, prod_op], modulo
addition_op = '+', '-'
addition = [addition, add_op], addition
logic_and = [logic_and, '&'], addition
logic_or = [logic_or, '|'], logic_and

comparison_op = '>', '<', '==', '!=', '>=', '<='
comparison = logic_or, {comparison_op, logic_or}

parameter_list = '(', [{atom, ','}, atom, ['.']], ')'
function_op = '->', '~>'
function_definition = parameter_list, function_op, expression

expression = function_definition

statement = [atom, '='] expression

program = {statement}
```
