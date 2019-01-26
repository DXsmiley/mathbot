import operator
import pytest
from random import randint

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

@pytest.mark.randomize(v=int, l=list_of(int))
def test_interleave_correct(v, l):
    asrt(f'interleave({v}, {l}) == {list(joinit(l, v))}')

def test_flatten_list():
    l = gen_random_deep_list()
    
    asrt(f'flatten({l}) == {list(flatten(l))}')

@pytest.mark.randomize(l=list_of(int))
def test_in_for_list(l):
    if len(l) == 0:
        return
    
    x = l[randint(0, len(l) - 1)]
    asrt(f'in({l}, {x})')
    asrt(f'!in({l}, ;h)')

def test_assoc_create_get():
    asrt('''
    ass = foldr((a,b) -> assoc(b, a, a), [], range(1,10)),
    ass_bool = map(a -> get(ass, a) == a, range(1,10)),
    foldr((a,b) -> a && b, true, ass_bool)
    ''')

def test_assoc_remove():
    asrt('''
    ass = foldr((a,b) -> assoc(b, a, a), [], range(1,10)),
    ass_removed = foldr((a,b) -> aremove(b, a), ass, range(1,10)),
    ass_removed == [] && sort(ass) == zip(range(1,10), range(1,10))
    ''')

def test_assoc_values_keys():
    asrt('''
    ass = foldr((a,b) -> assoc(b, a, a), [], range(1,10)),
    sort(values(ass)) == range(1,10),
    sort(keys(ass)) == range(1,10)
    ''')

def test_assoc_update():
    asrt('''
    ass = foldr((a,b) -> assoc(b, a, a), [], range(1,10)),
    ass_squared = values(update(ass, 5, x -> x * x)),
    sort(ass_squared) == [1,2,3,4,6,7,8,9,25]
    ''')

def test_set_equals():
    asrt('''
    f = () -> 2,
    set_equals([5,1,"hi",;b,0,true,f],[;b,f,"hi",1,true,5,0]) && 
    !set_equals([5,1,"hi",;b,0,true,f],[;c,f,"hi",1,true,5,0])
    ''')

def test_set_create():
    asrt('''
    lst1 = [2,1,3,7,1,2,1,5,2,3],
    lst2 = [1,2,3,5,7,1,2,3,5,7],
    sort(to_set(lst1)) == sort(to_set(lst2))
    ''')