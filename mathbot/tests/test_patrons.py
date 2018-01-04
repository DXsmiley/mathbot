import pytest
import core.parameters

@pytest.fixture(scope = 'function')
def patrons():
    core.parameters.reset()
    import patrons
    patrons.PATRONS = {}
    yield patrons


def test_simple_rankings(patrons):
    core.parameters.add_source({'patrons': {
        '1': 'none',
        '2': 'constant',
        '3': 'quadratic',
        '4': 'exponential',
        '5': 'special'    
    }})
    assert patrons.tier('1') == patrons.TIER_NONE
    assert patrons.tier('2') == patrons.TIER_CONSTANT
    assert patrons.tier('3') == patrons.TIER_QUADRATIC
    assert patrons.tier('4') == patrons.TIER_EXPONENTIAL
    assert patrons.tier('5') == patrons.TIER_SPECIAL


def test_complex_rankings(patrons):
    core.parameters.add_source({'patrons': {
        '56347856': 'none - Something extra',
        '68362367': 'constantkjdsgh',
        '27456542': 'quadraticsdkfjghdfks',
        '57235548': 'exponentialhfgjd',
        '58563757': 'special---98w475\'\'ekhjf'
    }})
    assert patrons.tier('75635675') == patrons.TIER_NONE
    assert patrons.tier('26374267') == patrons.TIER_NONE
    assert patrons.tier('56347856') == patrons.TIER_NONE
    assert patrons.tier('68362367') == patrons.TIER_CONSTANT
    assert patrons.tier('27456542') == patrons.TIER_QUADRATIC
    assert patrons.tier('57235548') == patrons.TIER_EXPONENTIAL
    assert patrons.tier('58563757') == patrons.TIER_SPECIAL


def test_invalid_ranking(patrons):
    with pytest.raises(ValueError):
        core.parameters.add_source({'patrons': {
            '1': 'something'
        }})
        assert patrons.tier('1') == patrons.TIER_NONE