import pytest
import os

from core.parameters import add_source, get

def test_parameters():
    add_source({'test-1': 'first'})
    add_source({'test-1': 'second'})
    add_source({'test-1': 'third'})
    add_source({'test-2': 'value'})
    add_source({'test-2': {'dict': True}})
    add_source({'test-3': 'env:core_parameter_test'})
    add_source({'test-4': 'escape:string'})

    os.environ['core_parameter_test'] = 'result'

    assert get('test-1') == 'third'
    assert get('test-2') == {'dict': True}
    assert get('test-3') == 'result'
    assert get('test-4') == 'string'

    with pytest.raises(Exception):
        add_source({'should_raise': True})
