import operator
import pytest

from test_calc_helpers import *

def list_of(thetype, min_items=0, max_items=20):
    return pytest.list_of(thetype,
                          min_items=min_items,
                          max_items=max_items)

def _test_bin_op(name, func):
    @pytest.mark.randomize(a=int, b=int)
    def _internal(a, b):
        dort(f'{name}({a}, {b})', func(a, b))
    return _internal

test_sum = _test_bin_op('sum', operator.add)
test_mul = _test_bin_op('mul', operator.mul)
test_dif = _test_bin_op('dif', operator.sub)
test_dif = _test_bin_op('max', max)
test_dif = _test_bin_op('min', min)

@pytest.mark.randomize(x=list_of(int))
def test_reverse_length(x):
    asrt(f'length(reverse({x})) == length({x})')

@pytest.mark.randomize(x=list_of(int))
def test_reverse_twice(x):
    asrt(f'reverse(reverse({x})) == {x}')

@pytest.mark.randomize(x=list_of(int))
def test_reverse_maintains_elements(x):
    asrt(f'sort(reverse({x})) == sort({x})')

@pytest.mark.randomize(x=list_of(int))
def test_sort_length(x):
    asrt(f'length(sort({x})) == length({x})')

@pytest.mark.randomize(x=list_of(int))
def test_sort_multiapplication(x):
    asrt(f'sort(sort({x})) == sort({x})')

@pytest.mark.randomize(x=list_of(int))
def test_sort_sorted(x):
    asrt(fr'''
        sorted(k) = if(length(k) <= 1, true, ('k <= '\k) && sorted(\k))
        sorted(sort({x}))
    ''')

@pytest.mark.randomize(x=list_of(int), y=list_of(int))
def test_zip_length(x, y):
    asrt(f'length(zip({x}, {y})) == min(length({x}), length({y}))')

@pytest.mark.randomize(n=int, min_num=0, max_num=20)
def test_repeat_length(n):
    asrt(f'length(repeat(true {n})) == {n}')

@pytest.mark.randomize(n=int, v=int, min_num=0, max_num=20)
def test_repeat_correct_values(n, v):
    asrt(f'foldl(and true map((x) -> x == {v}, repeat({v} {n})))')
