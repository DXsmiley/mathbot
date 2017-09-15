from calculator.new_interpereter import test as _calc
from calculator.errors import EvaluationError


def calculate(equation, stop_errors = False):
    return _calc(equation)
