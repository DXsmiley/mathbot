import pytest
import modules.latex

# Not a test, but % symbols in there are known to break things
def test_template_symbols():
	assert('%' not in modules.latex.PREAMBLE)
	assert('%' not in modules.latex.TEMPLATE)
