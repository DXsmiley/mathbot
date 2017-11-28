import calculator.functions
import sympy


class TooMuchOutputError(Exception):

    pass


class Collector:

    def __init__(self, limit = None):
        self.parts = []
        self.length = 0
        self.limit = limit

    def print(self, *args):
        self.parts += args
        self.length += sum(map(len, args))
        if self.limit and self.length > self.limit:
            raise TooMuchOutputError

    def drop(self):
        self.parts.pop()

    def __str__(self):
        output = ''.join(self.parts)
        if self.limit and len(output) > self.limit:
            output = output[:self.limit - 3] + '...'
        return output


def f(v, c):
    if isinstance(v, calculator.functions.Array):
        c.print('[')
        for i in v.items:
            f(i, c)
            c.print(', ')
        c.drop()
        c.print(']')
    else:
        c.print(str(v))


def format(value, limit = None):
    col = Collector(limit = limit)
    f(value, col)
    return str(col)


def l(v, c):
    if isinstance(v, calculator.functions.Array):
        c.print(r'\left\[')
        for i in v.items:
            l(i, c)
            c.print(', ')
        c.drop()
        c.print(r'\right\]')
    else:
        try:
            c.print(sympy.latex(v))
        except Exception:
            c.print(str(v))


def latex(value, limit = None):
    col = Collector(limit = limit)
    l(value, col)
    return str(col)