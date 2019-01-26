:::topics turing-functions turing-library

# Calc command builtin functions

## Operator replacements

```
sum (a b) -> a + b
mul (a b) -> a * b
dif (a b) -> a - b
div (a b) -> a / b
pow (a b) -> a ^ b
mod (a b) -> a ~mod b
and (a b) -> a && b
 or (a b) -> a || b
```

## Comparitor utilities

### `max(a, b)`
Returns the larger of a and b, as compared by `<`.
If they are considered 'equal', will return a.

### `min(a, b)`
Returns the smaller of a and b, as compared by `<`.
If they are considered 'equal', will return a.

:::page-break

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

:::page-break

### `reduce(function, sequence)`
Example:
```
reduce(sum, array(0, 1, 2, 3, 4))
```
produces
```
10
```

### `interleave(element, sequence)`
Example:
```
interleave(;, "hello")
```
produces
```
"h,e,l,l,o"
```

### `flatten(sequence)`
Flattens a list of lists.
Example:
```
flatten([[1 2] [3 4]])
```
produces
```
[1 2 3 4]
```

### `in(a, sequence)`
Checks if a is in the sequence.

### `apair(a, b)`
Creates a new key-value pair from two objects.

### `akey(pair)`
Gets the key of a key-value pair.

### `avalue(pair)`
Gets the value of a key-value pair.

### `assoc(assoc-list, key, value)`
Associates a key with a value in the association list given.
Example:
```
assoc([["a" 1] ["b" 2] ["c" 3]] "hello" 55)
``` 
produces
```
[["a" 1] ["b" 2] ["c" 3] ["hello" 55]]
```

### `aremove(assoc-list, key)`
Removes the given key from the assoc list.

### `aremove_value(assoc-list, value)`
Removes the all given values from the assoc list.

### `update(assoc-list, key, function)`
Updates the value of the key using function in the given association list.

:::page-break

### `to-set(list)`
Converts a list to a set.

### `set_insert(set a)`
Add the object a to the set.

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
