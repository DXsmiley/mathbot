import calculator.functions
import calculator.errors
import sympy


ALL_SYMPY_CLASSES = tuple(sympy.core.all_classes)


class Collector:

    def __init__(self, limit = None):
        self.parts = []
        self.length = 0
        self.limit = limit

    def print(self, *args):
        self.parts += args
        self.length += sum(map(len, args))
        if self.limit and self.length > self.limit:
            raise calculator.errors.TooMuchOutputError

    def drop(self):
        self.parts.pop()

    def __str__(self):
        output = ''.join(self.parts)
        if self.limit and len(output) > self.limit:
            output = output[:self.limit - 3] + '...'
        return output


# Format an iterable object that supports .head and .rest
def format_iterable(function, iterable, collector):
    while iterable:
        function(iterable.head, collector)
        iterable = iterable.rest
        if iterable:
            collector.print(', ')


def f(v, c):
    if v is None:
        c.print('null')
    elif isinstance(v, calculator.functions.Array):
        c.print('array(')
        format_iterable(f, v, c)
        c.print(')')
    elif isinstance(v, calculator.functions.ListBase):
        c.print('list(')
        format_iterable(f, v, c)
        c.print(')')
    else:
        c.print(str(v))


def format(value, limit = None):
    col = Collector(limit = limit)
    f(value, col)
    return str(col)


def l(v, c):
    if isinstance(v, (calculator.functions.Array, calculator.functions.ListBase)):
        c.print(r'\left\[')
        format_iterable(l, v, c)
        c.print(r'\right\]')
    elif isinstance(v, ALL_SYMPY_CLASSES):
        c.print(sympy.latex(c))
    else:
        c.print(str(v))


def latex(value, limit = None):
    col = Collector(limit = limit)
    l(value, col)
    return str(col)
