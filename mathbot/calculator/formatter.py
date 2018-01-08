import sympy
import calculator.functions
import calculator.errors


ALL_SYMPY_CLASSES = tuple(sympy.core.all_classes)


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


# class CustomStringPrinter(sympy.printing.str.StrPrinter):

#     def _print_I(self, expr):
#         return '**I**'

#     def _print_Mul(self, expr):
#         a, b = i.as_two_terms()
#         if 


class SimpleFormatter:

    def __init__(self, limit=None):
        self._collector = Collector(limit=limit)

    def drop(self):
        ''' Remove the most recently added item '''
        self._collector.drop()

    def fm(self, *args):
        ''' Format a number of objects '''
        for i in args:
            # print(i.__class__, i.__class__.__mro__)
            if i is None:
                self._collector.print('null')
            elif isinstance(i, str):
                self.fm_string(i)
            elif isinstance(i, list):
                self.fm_py_list(i)
            elif isinstance(i, calculator.functions.Array):
                self.fm_array(i)
            elif isinstance(i, calculator.functions.ListBase):
                self.fm_list(i)
            else:
                self.fm_string(str(i))

    def fm_iterable(self, name, iterable):
        ''' Format an iterable object that supports .head and .rest '''
        self.fm(name, '(')
        while iterable:
            self.fm(iterable.head)
            iterable = iterable.rest
            if iterable:
                self.fm(', ')
        self.fm(')')

    def fm_string(self, i):
        ''' Format a string, which means just add it to the output '''
        self._collector.print(i)

    def fm_array(self, i):
        ''' Format an array '''
        self.fm_iterable('array', i)

    def fm_list(self, i):
        ''' Format a list '''
        self.fm_iterable('list', i)

    def fm_py_list(self, ls):
        ''' Formay a python list '''
        self.fm('(')
        for i in ls:
            self.fm(i, ', ')
        if ls:
            self.drop()
        self.fm(')')

    def __str__(self):
        return str(self._collector)


class DiscordFormatter(SimpleFormatter):

    def fm_string(self, i):
        i = i.replace('*', '\\*')
        i = i.replace('_', '\\_')
        self._collector.print(i)


def format(*values, limit=None):
    fmtr = SimpleFormatter(limit=limit)
    fmtr.fm(*values)
    return str(fmtr)
