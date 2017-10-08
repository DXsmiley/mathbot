from calculator.errors import *
import calculator.operators
import asyncio
import math
import cmath
import random
import calculator.attempt6


DIGITS_LIMIT = 2000


def except_math_error(f, name="name not provided"):
    def internal(*x):
        try:
            return f(*x)
        except Exception:
            if len(x) == 0:
                raise EvaluationError(
                    'Can\'t run {} function with no arguments.'.format(name))
            elif len(x) == 1:
                formatted = calculator.errors.format_value(x[0])
                raise EvaluationError(
                    'Can\'t run {} function on value {}'.format(
                        name, formatted))
            else:
                formatted = ', '.join(map(calculator.errors.format_value, x))
                raise EvaluationError(
                    'Can\'t run {} function on values ({})'.format(
                        name, formatted))
    internal.__name__ = f.__name__
    return internal


class DoubleEndedArray:

    def __init__(self, values):
        self.front = []
        self.back = values[:]

    def __getitem__(self, index):
        if index < 0:
            return self.front[abs(index) - 1]
        return self.back[index]

    def __setitem__(self, index, value):
        if index < 0:
            self.front[abs(index) - 1] = value
        else:
            self.back[index] = value

    def __len__(self):
        return len(self.front) + len(self.back)

    def append(self, item):
        self.back.append(item)

    def prepend(self, item):
        self.front.append(item)


class BaseFunction:
    pass


class Array(BaseFunction):

    def __init__(self, values):
        # self.front = []
        self.back = values
        # self.has_ownership = True
        self.values = list(values)
        if len(values) > 128:
            raise EvaluationError(
                'Created an array with more than 128 elements. This limitation \
is in place while the feature is in the development.')

    def call(self, arguments, interpereter):
        if len(arguments) != 1 or not isinstance(
            arguments[0], int) or not (
            0 <= arguments[0] < len(
                self.values)):
            raise EvaluationError(
                'Attempted to get non-existent value of array')
        return self.values[arguments[0]]

    def __str__(self):
        return 'array({})'.format(', '.join(map(str, self.values)))


class Function(BaseFunction):

    def __init__(self, parameters, expression, scope, variadic):
        self.parameters = parameters
        self.expression = expression
        self.scope = scope
        self.cache = {}
        self.variadic = variadic

    def call(self, arguments, interpereter):
        # TODO: setup scope
        if len(arguments) > 128:
            raise EvaluationError(
                'No more than 128 arguments may be passed to a function at once.')
        if self.variadic:
            if len(arguments) < len(self.parameters) - 1:
                raise EvaluationError(
                    'Incorrect number of arguments for function.')
        else:
            if len(arguments) != len(self.parameters):
                raise EvaluationError(
                    'Incorrect number of arguments for function.')
        tp = tuple(arguments)
        if tp not in self.cache:
            if self.variadic:
                extra_arguments = arguments[len(self.parameters) - 1:]
                main_arguments = arguments[:len(self.parameters)]
                values = {key: value for key, value in zip(
                    self.parameters[:-1], main_arguments)}
                values[self.parameters[-1]] = Array(extra_arguments)
                subscope = Scope(self.scope, values)
                self.cache[tp] = yield from ev(self.expression, subscope, interpereter)
            else:
                subscope = Scope(
                    self.scope, {
                        key: value for key, value in zip(
                            self.parameters, arguments)})
                self.cache[tp] = yield from ev(self.expression, subscope, interpereter)
        return self.cache[tp]

    def __str__(self):
        return 'user defined function'


class BuiltinFunction(BaseFunction):

    def __init__(self, function, name=None):
        self.function = function
        self.name = name or self.function.__name__

    def call(self, arguments, interpereter):
        return self.function(*arguments)
        yield

    def __str__(self):
        return 'builtin function {}'.format(self.name)


class BuiltinCoroutine(BaseFunction):

    def __init__(self, function):
        self.function = function

    def call(self, arguments, interpereter):
        raise NotImplementedException


class BuiltinGenerator(BaseFunction):

    def __init__(self, function):
        self.function = function

    def call(self, arguments, interpereter):
        return (yield from self.function(*arguments))

    def __str__(self):
        return 'builtin function "{}"'.format(self.function.__name__)


class MacroArgumentFunction(BaseFunction):

    __slots__ = ['function']

    def __init__(self, function):
        self.function = function

    def call(self, arguments, interpereter):
        if len(arguments) != 0:
            raise EvaluationError(
                'Macro argument functions take no arguments.')
        return self.function()

    def __call__(self):
        return self.function()

    def __str__(self):
        return 'macro argument function'


# A Macro is a function where the arguments are functions which can
# be called to get the ACTUAL values. Used to implement things like
# if statements
class Macro:

    def __init__(self, function):
        self.function = function

    def call(self, *args):
        return (yield from self.function.call(*args))

    def __str__(self):
        return str(self.function)


class List:

    def __init__(self, values):
        self.values = list(values)

    def __getitem__(self, index):
        return self.values[index]

    def __len__(self):
        return len(self.values)


class Scope:

    def __init__(self, previous, values, protected_names=None):
        self.values = values
        self.previous = previous
        self.protected_names = protected_names
        if self.protected_names is None and self.previous is not None:
            self.protected_names = self.previous.protected_names

    def __getitem__(self, key):
        try:
            return self.values[key]
        except KeyError:
            try:
                return self.previous[key]
            except TypeError:
                raise EvaluationError('Unknown name: {}'.format(key))

    def __setitem__(self, key, value):
        if self.protected_names is not None and key in self.protected_names:
            raise EvaluationError(
                '\'{}\' is a protected constant and cannot be overridden'.format(key))
        self.values[key] = value

    def clear_cache(self, seen=None):
        if seen is None:
            seen = set()
        if self not in seen:
            seen.add(self)
            if self.previous is not None:
                self.previous.clear_cache()
            for key, value in self.values.items():
                if isinstance(value, Function):
                    value.cache = {}
                    value.scope.clear_cache(seen)

    def __repr__(self):
        return '{} -> {}'.format(repr(self.values), repr(self.previous))


def if_statement(*arguments):
    if len(arguments) < 3:
        raise EvaluationError('Too few arguments for if function. Requires 3.')
    if len(arguments) > 3:
        raise EvaluationError(
            'Too many arguments for if function. Requires 3.')
    condition, if_true, if_false = arguments
    if (yield from condition()):
        return (yield from if_true())
    return (yield from if_false())


def switch_statement(*arguments):
    if len(arguments) % 2 == 0 or len(arguments) < 3:
        raise EvaluationError(
            'Invalid number of arguments for switch expression')
    for i in range(0, len(arguments) - 2, 2):
        if (yield from arguments[i]()):
            return (yield from arguments[i + 1]())
    return (yield from arguments[-1]())


def func_map(function, iterable):
    if not isinstance(iterable, List):
        raise EvaluationError('Cannot run map function on non-List')
    return List(map(function, ))


def mergemany(*args):
    r = {}
    for i in args:
        for k, v in i.items():
            assert(k not in r)
            r[k] = v
    return r


def oneify(x):
    return 1 if x else 0


def is_function(x):
    return oneify(isinstance(x, BaseFunction) or isinstance(x, Macro))


def is_real(x):
    return oneify(isinstance(x, int) or isinstance(x, float))


def is_complex(x):
    return oneify(isinstance(x, complex))


def array_length(x):
    if not isinstance(x, Array):
        raise EvaluationError('Cannot get the length of non-array object')
    return len(x.values)


def array_splice(array, start, end):
    if not isinstance(array, Array):
        raise EvaluationError('Cannot splice non-array')
    if not isinstance(start, int) or not isinstance(end, int):
        raise EvaluationError('Non-integer indexes passed to splice')
    # TODO: Make this efficient
    return Array(array.values[start:end])

# TODO: Make this more efficient


def array_join(*items):
    if len(items) == 0:
        raise EvaluationError('Cannot join no arrays together.')
    result = []
    for i in items:
        if not isinstance(i, Array):
            raise EvaluationError('Cannot call join on non-array')
        result += i.values
    return Array(result)


class Expanded:

    def __init__(self, arrays):
        self.arrays = arrays

    def __iter__(self):
        for i in self.arrays:
            yield from i.values

    def __str__(self):
        return 'expanded_array'


def array_expand(*arrays):
    for i in arrays:
        if not isinstance(i, Array):
            raise EvaluationError('Cannot expand non-array')
    return Expanded(arrays)


# Changes a trig function to take degrees as its arguments
def fdeg(func):
    return lambda x: func(math.radians(x))


# Changes a trig function to produce degrees as its output
def adeg(func):
    return lambda x: math.degrees(func(x))


def m_choose(n, k):
    return calculator.operators.operator_division(
        calculator.operators.function_factorial(n),
        calculator.operators.operator_multiply(
            calculator.operators.function_factorial(k),
            calculator.operators.function_factorial(
                calculator.operators.operator_subtract(
                    n,
                    k
                )
            )
        )
    )


def maybe_complex(f_real, f_complex, name):
    def internal(x):
        if isinstance(x, complex):
            return f_complex(x)
        return f_real(x)
    return except_math_error(internal, name)


BUILTIN_FUNCTIONS = {
    # 'interval': lambda a, b: List(range(a, b)),
    'sin': maybe_complex(math.sin, cmath.sin, "sine"),
    'cos': maybe_complex(math.cos, cmath.cos, "cosine"),
    'tan': maybe_complex(math.tan, cmath.tan, "tangent"),
    'sind': except_math_error(fdeg(math.sin), "sine"),
    'cosd': except_math_error(fdeg(math.cos), "cosine"),
    'tand': except_math_error(fdeg(math.tan), "tangent"),
    'asin': maybe_complex(math.asin, cmath.asin, "arcsine"),
    'acos': maybe_complex(math.acos, cmath.acos, "arccosine"),
    'atan': maybe_complex(math.atan, cmath.atan, "arctangent"),
    'asind': except_math_error(adeg(math.asin), "arcsine"),
    'acosd': except_math_error(adeg(math.acos), "arccos"),
    'atand': except_math_error(adeg(math.atan), "arctan"),
    'sinh': maybe_complex(math.sinh, cmath.sinh, "hyperbolic sine"),
    'cosh': maybe_complex(math.cosh, cmath.cosh, "hyperbolic cosine"),
    'tanh': maybe_complex(math.tanh, cmath.tanh, "hyperbolic tangent"),
    'asinh': maybe_complex(math.asinh, cmath.asinh, "inverse hyperbolic sine"),
    'acosh': maybe_complex(math.acosh, cmath.acosh, "inverse hyperbolic cosine"),
    'atanh': maybe_complex(math.atanh, cmath.atanh, "inverse hyperbolic tangent"),
    'deg': except_math_error(math.degrees, "to degrees"),
    'rad': except_math_error(math.radians, "to radians"),
    'log': calculator.operators.function_logarithm,
    'ln': maybe_complex(math.log, cmath.log, "natural logarithm"),
    'round': except_math_error(round, "round"),
    'int': except_math_error(int, "int"),
    'sqrt': except_math_error(lambda x: x ** 0.5, "square root"),
    'gamma': except_math_error(lambda x: calculator.operators.function_factorial(x - 1), "gamma"),
    'gcd': calculator.operators.function_gcd,
    'lcm': calculator.operators.function_lcm,
    'choose': m_choose,
    'is_real': is_real,
    'is_complex': is_complex,
    'is_function': is_function,
    'length': array_length,
    'join': array_join,
    'splice': array_splice,
    'expand': array_expand,
    'im': except_math_error(lambda x: x.imag, "im"),
    're': except_math_error(lambda x: x.real, "re")
}


FIXED_VALUES = {
    'e': math.e,
    'pi': math.pi,
    'π': math.pi,
    'tau': math.pi * 2,
    'τ': math.pi * 2,
    'i': 1j,
    'euler_gamma': 0.577215664901,
    'true': 1,
    'false': 0
}


CONSTANTS = mergemany(
    {
        'if': Macro(BuiltinGenerator(if_statement)),
        'switch': Macro(BuiltinGenerator(switch_statement))
    },
    FIXED_VALUES,
    {k: BuiltinFunction(v, name=k) for k, v in BUILTIN_FUNCTIONS.items()}
)


ROOT_SCOPE = Scope(None, CONSTANTS, set(CONSTANTS))


def new_scope():
    return Scope(ROOT_SCOPE, {})


def rolldie(times, faces):
    if isinstance(times, float):
        times = int(times)
    if isinstance(faces, float):
        faces = int(faces)
    if not isinstance(times, int) or not isinstance(faces, int):
        raise EvaluationError('Cannot roll {} dice with {} faces'.format(
            calculator.errors.format_value(times),
            calculator.errors.format_value(faces)
        ))
    if times < 1:
        return 0
    if times > 1000:
        raise EvaluationError('Cannot roll more than 1000 dice')
    if faces < 1:
        raise EvaluationError('Cannot roll die with less than one face')
    if isinstance(faces, float) and not faces.is_integer():
        raise EvaluationError(
            'Cannot roll die with fractional number of faces')
    return sum(random.randint(1, faces) for i in range(times))


def wrap_ev(p, scope, it):
    def f():
        result = yield from ev(p, scope, it)
        if isinstance(result, Expanded):
            raise EvaluationError('Expanded ')
        return result
    return MacroArgumentFunction(f)


class Interpereter():

    def __init__(self, limit_stack_size):
        self.stack = []
        self.limit_stack_size = limit_stack_size
        self.warnings = set()

    def step(self):
        # print(self.stack)
        generator, injector = self.stack[-1]
        try:
            new_thing = next(generator)
            # print(new_thing)
            if new_thing is not None:
                if len(self.stack) >= self.limit_stack_size:
                    raise EvaluationError('Stack overflow: too much recursion')
                self.stack.append(new_thing)
        except StopIteration as e:
            injector.append(e.value)
            self.stack.pop()

    def add_warning(self, warning):
        self.warnings.add(warning)


async def evaluate(p, scope, limits):
    it = Interpereter(limits.get('stack_size', 200))
    for i in check_parse_tree_warnings(p):
        it.add_warning(i)
    inject = []
    it.stack.append((evaluate_step(p, scope, it), inject))
    while it.stack:
        work = 0
        while it.stack and work < 1000:
            it.step()
            work += 1
        await asyncio.sleep(0)
    result = inject[0]
    warnings = list(it.warnings)
    del it
    if limits.get('warnings', False):
        return warnings, result
    return result


def ev(p, scope, it):
    injector = []
    yield (evaluate_step(p, scope, it), injector)
    return injector[0]


OPERATOR_DICT = {
    '+': calculator.operators.operator_add,
    '-': calculator.operators.operator_subtract,
    '*': calculator.operators.operator_multiply,
    '/': calculator.operators.operator_division,
    '^': calculator.operators.operator_power,
    '%': calculator.operators.operator_modulo,
    '<': calculator.operators.operator_less,
    '>': calculator.operators.operator_more,
    '<=': calculator.operators.operator_less_equal,
    '>=': calculator.operators.operator_more_equal,
    '==': calculator.operators.operator_equal,
    '!=': calculator.operators.operator_not_equal,
    'd': rolldie,
    '&': lambda a, b: 1 if a and b else 0,
    '|': lambda a, b: 1 if a or b else 0
}


def convert_number(string):
    if string[-1] == 'i':
        return convert_number(string[:-1]) * 1j
    try:
        return int(string)
    except ValueError:
        pass
    return float(string)


def check_parse_tree_warnings(tree):
    if isinstance(tree, dict):
        for key, value in tree.items():
            if key is 'warning':
                yield value
            else:
                yield from check_parse_tree_warnings(value)


def evaluate_step(p, scope, it):
    while True:
        node_type = p['#']
        if node_type == 'number':
            return convert_number(p['string'])
        elif node_type == 'bin_op':
            left = yield from evaluate_step(p['left'], scope, it)
            right = yield from evaluate_step(p['right'], scope, it)
            op = OPERATOR_DICT.get(p['operator'])
            assert(op is not None)
            return op(left, right)
        elif node_type == 'not':
            value = yield from evaluate_step(p['expression'], scope, it)
            return 0 if value else 1
        elif node_type == 'die':
            times = (yield from evaluate_step(p['times'], scope, it)) if 'times' in p else 1
            faces = (yield from evaluate_step(p['faces'], scope, it))
            return rolldie(times, faces)
        elif node_type == 'udie':
            # THIS IS OLD
            faces = yield from evaluate_step(p['faces'], scope, it)
            return rolldie(1, faces)
        elif node_type == 'uminus':
            return - (yield from evaluate_step(p['value'], scope, it))
        elif node_type == 'function_call':
            function = yield from evaluate_step(p['function'], scope, it)
            if not isinstance(
                    function,
                    BaseFunction) and not isinstance(
                    function,
                    Macro):
                raise EvaluationError(
                    '{} is not a function'.format(
                        format_value(function)))
            # Get the list of AST objects
            items = p.get('arguments', {'items': []})['items']
            args = []
            # print(items)
            for i in items:
                if isinstance(function, Macro):
                    args.append(wrap_ev(i, scope, it))
                else:
                    value = yield from evaluate_step(i, scope, it)
                    if isinstance(value, Expanded):
                        args += list(value)
                    else:
                        args.append(value)
            return (yield from function.call(args, it))
        elif node_type == 'word':
            name = p['string'].lower()
            return scope[name]
        elif node_type == 'factorial':
            return calculator.operators.function_factorial(
                (yield from evaluate_step(p['value'], scope, it)))
        elif node_type == 'assignment':
            name = p['variable']['string'].lower()
            value = yield from evaluate_step(p['value'], scope, it)
            scope[name] = value
            return value
        elif node_type == 'statement_list':
            yield from ev(p['statement'], scope)
            p = p['next']
        elif node_type == 'program':
            result = 0
            for i in p['items']:
                result = yield from ev(i, scope, it)
            return result
        elif node_type == 'function_definition':
            parameters = [i['string'].lower()
                          for i in p['parameters']['items']]
            function = Function(
                parameters,
                p['expression'],
                scope,
                p['variadic'])
            if p['kind'] == '~>':
                function = Macro(function)
            return function
        elif node_type == 'comparison':
            previous = yield from evaluate_step(p['first'], scope, it)
            for i in p['rest']:
                op = i['operator']
                current = yield from evaluate_step(i['value'], scope, it)
                if not OPERATOR_DICT[op](previous, current):
                    return 0
                previous = current
            return 1
        elif node_type == 'output':
            result = yield from evaluate_step(p['expression'], scope, it)
            print(result)
            return result
        else:
            return None


def calculate(equation, scope=None, stop_errors=False, limits={}):
    to, result = calculator.attempt6.parse(equation)
    assert(result is not None)
    loop = asyncio.get_event_loop()
    future = evaluate(result, scope or new_scope(), limits)
    return loop.run_until_complete(future)


def calculate_async(equation, scope=None, limits={}, stop_errors=False):
    to, result = calculator.attempt6.parse(equation)
    if result is None:
        raise ParseFailed(' '.join(to.tokens), to.rightmost)
    return evaluate(result, scope or new_scope(), limits)


if False:

    word = ReToken(r'[a-zA-Z_][a-zA-Z0-9_]*')
    pipe = Supress(Token('|'))
    colon = Supress(Token(':'))
    equals = Supress(Token('='))
    lpar = Supress(Token('('))
    rpar = Supress(Token(')'))
    comma = Supress(Token(','))

    attrib = word('key') + colon + word('value')
    attributes = attrib('first') | attrib('first') + attributes('rest')
    rule = word('name') + ~(colon + word)('')
    atom = rule | (lpar + options + ~(comma + attributes)('attributes') + rpar)
    sequence = Attach(atom('first') + ~sequence('rest'), {'type': sequence})
    options = sequence | Attach(
        options('left') + pipe + sequence('right'), {'type': sequence})
    statement = word('name') + equals + options('statement')
    grammar = Repeat(statement)
