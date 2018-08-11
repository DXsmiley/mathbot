import pytest
import core.parameters
import patrons


def test_simple_rankings(patrons):
    p = core.parameters.load_parameters({'patrons': {
        '2': 'constant',
        '3': 'quadratic',
        '4': 'exponential',
        '5': 'special'    
    }})
    assert patrons.tier(p, '1') == patrons.TIER_NONE
    assert patrons.tier(p, '2') == patrons.TIER_CONSTANT
    assert patrons.tier(p, '3') == patrons.TIER_QUADRATIC
    assert patrons.tier(p, '4') == patrons.TIER_EXPONENTIAL
    assert patrons.tier(p, '5') == patrons.TIER_SPECIAL


def test_complex_rankings(patrons):
    p = core.parameters.load_parameters({'patrons': {
        '56347856': 'none - Something extra',
        '68362367': 'constantkjdsgh',
        '27456542': 'quadraticsdkfjghdfks',
        '57235548': 'exponentialhfgjd',
        '58563757': 'special---98w475\'\'ekhjf'
    }})
    assert patrons.tier(p, '75635675') == patrons.TIER_NONE
    assert patrons.tier(p, '26374267') == patrons.TIER_NONE
    assert patrons.tier(p, '56347856') == patrons.TIER_NONE
    assert patrons.tier(p, '68362367') == patrons.TIER_CONSTANT
    assert patrons.tier(p, '27456542') == patrons.TIER_QUADRATIC
    assert patrons.tier(p, '57235548') == patrons.TIER_EXPONENTIAL
    assert patrons.tier(p, '58563757') == patrons.TIER_SPECIAL


def test_invalid_ranking(patrons):
    with pytest.raises(patrons.InvalidPatronRankError):
        p = core.parameters.load_parameters({'patrons': {
            '1': 'something'
        }})
        patrons.tier(p, '1')
