''' Calculator formatter.

    Used to take complicated data structures, including
    lists, arrays, and sympy objects and convert them
    into a flat, human-readable string.
'''

import sympy
import calculator.functions
import calculator.errors


ALL_SYMPY_CLASSES = tuple(sympy.core.all_classes) # pylint: disable=no-member


class Collector:

    ''' Buffers print-like commands in order to make things
        fast and also limit the total size of the output.
    '''

    def __init__(self, limit=None):
        self.parts = []
        self.length = 0
        self.limit = limit

    def print(self, *args):
        ''' Add some stuff to the buffer.
            Raises an exception if it overlfows.
        '''
        self.parts += args
        self.length += sum(map(len, args))
        if self.limit and self.length > self.limit:
            raise calculator.errors.TooMuchOutputError

    def drop(self):
        ''' Remove the last item from the buffer. '''
        self.parts.pop()

    def __str__(self):
        ''' Reduce to a string. '''
        output = ''.join(self.parts)
        if self.limit and len(output) > self.limit:
            output = output[:self.limit - 3] + '...'
        return output


class SimpleFormatter:

    ''' Simplest implementation of the formatter.
        Currently used to format things in all cases,
        but in theory could be subclassed to produce
        different behaviour for specific cases.
    '''

    def __init__(self, limit=None):
        self._collector = Collector(limit=limit)

    def drop(self):
        ''' Remove the most recently added item '''
        self._collector.drop()

    def fmt(self, *args):
        ''' Format a number of objects '''
        for i in args:
            # print(i.__class__, i.__class__.__mro__)
            if i is None:
                self._collector.print('null')
            elif isinstance(i, str):
                self.fmt_string(i)
            elif isinstance(i, list):
                self.fmt_py_list(i)
            elif isinstance(i, calculator.functions.Array):
                self.fmt_array(i)
            elif isinstance(i, calculator.functions.ListBase):
                self.fmt_list(i)
            else:
                self.fmt_string(str(i))

    def fmt_iterable(self, name, iterable):
        ''' Format an iterable object that supports .head and .rest '''
        self.fmt(name, '(')
        while iterable:
            self.fmt(iterable.head)
            iterable = iterable.rest
            if iterable:
                self.fmt(', ')
        self.fmt(')')

    def fmt_string(self, i):
        ''' Format a string, which means just add it to the output '''
        self._collector.print(i)

    def fmt_array(self, i):
        ''' Format an array '''
        self.fmt_iterable('array', i)

    def fmt_list(self, i):
        ''' Format a list '''
        self.fmt_iterable('list', i)

    def fmt_py_list(self, lst):
        ''' Formay a python list '''
        self.fmt('(')
        for i in lst:
            self.fmt(i, ', ')
        if lst:
            self.drop()
        self.fmt(')')

    def __str__(self):
        return str(self._collector)


def format(*values, limit=None): # pylint: disable=redefined-builtin
    ''' Format some values, producing a human-readable string. '''
    fmtr = SimpleFormatter(limit=limit)
    fmtr.fmt(*values)
    return str(fmtr)
