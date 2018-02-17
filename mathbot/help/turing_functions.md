# Calc command builtin functions

## Operator replacements

### `sum(a, b)`
Returns `a + b`.

### `product(a, b)`
Returns `a * b`.

### `difference(a, b)`
Returns `a - b`.

### `quotient(a, b)`
Returns `a / b`.

### `power(a, b)`
Returns `a ^ b`.

### `modulo(a, b)`
Returns `a % b`.

## Comparitor utilities

### `max(a, b)`
Returns the larger of a and b, as compared by `>`.
If they are considered 'equal', will return b.

### `min(a, b)`
Returns the smaller of a and b, as compared by `<`.
If they are considered 'equal', will return b.

## Sequence manipulation

### `zip(a, b)`
Takes in two *sequences* and returns a *list* containing lists of pairs of elements from the two sequences.

The length of the result will be equal to the length of the shorter input sequence.

Example:
```
zip(list(1, 2, 3), list(4, 5, 6))
```
produces
```
list(list(1, 4), list(2, 5), list(3, 6))
```

### `zipmap(function, a, b)`
Similar to `map`, but iterates over two sequences at once. Equivilent to `zipmap (f, a, b) -> map((x) -> f('x, '\x), zip(a, b))`.

### `repeat(item, times)`
Returns a *list* with the item `item` repeated `times` times.

### `reverse(seq)`
Takes a *sequence* `seq` and produces a *list* containing `seq`'s elements in reverse order.

### `map(function, sequence)`
Apply's `function` to all the elements in `sequence` and produces a *list*.

### `filter(predicate, sequence)`
Produces a *list* containing the items in `sequence` for which the predicate returns a truthy value.

Example:
```
is_even(x) -> x % 2 == 0,
filter(is_even, list(4, 8, 3, 6, 3, 7, 8))
```
produces
```
list(4, 8, 6, 8)
```

### `reduce(function, sequence)`
Example:
```
reduce(sum, array(0, 1, 2, 3, 4))
```
produces
```
10
```

### `array(...)` (variadic)
Produces an array containing the specified elements.

### `list(...)` (variadic)
Produces a list containing the specified elements.

### `toarray(sequence)`
Converts `sequence` into an *array*.

### `tolist(sequence)`
Converts `sequence` into a *list*.

## String manipulation
These functions are designed to be used with strings, but may also be applied to other lists and arrays, since they are generic. No guarantees about whether they will work in this regard is made.

### `startswith(haystack needle)`
Returns whether `haystack` begins with `needle`.

### `drop(number sequence)`
Removes the first `number` elements from `sequences`.

### `split(haystack needle)`
Breaks apart the `haystack` by every `needle` found. Returns a sequence of strings.

Example:
```
split("this is a sentence", " ")
```
Produces:
```
["this", "is", "a", "sentence"]
```

### `display(...)` (variadic)
Takes any number of arguments and produces a string with the values in a human-readable format. Values are seperated by spaces.

### `ord(glyph)`
Returns an integral representation for the `glyph`.

### `chr(integer)`
Returns the glyph represented by `integer`.
