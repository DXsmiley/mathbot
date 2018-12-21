import pytest
import os

from core.parameters import load_parameters

def test_parameters():

    os.environ['core_parameter_test'] = 'result'

    parameters = load_parameters([
        {'test-1': 'first'},
        {'test-1': 'second'},
        {'test-1': 'third'},
        {'test-2': 'value'},
        {'test-2': {'dict': True}},
        {'test-3': 'env:core_parameter_test'},
        {'test-4': 'escape:string'}
    ])

    assert parameters.get('test-1') == 'third'
    assert parameters.get('test-2') == {'dict': True}
    assert parameters.get('test-2.dict') == True
    assert parameters.get('test-3') == 'result'
    assert parameters.get('test-4') == 'string'
