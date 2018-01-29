import core.parameters

TIER_NONE = 0
TIER_CONSTANT = 1
TIER_QUADRATIC = 2
TIER_EXPONENTIAL = 3
TIER_SPECIAL = 4

PATRONS = {}
loaded = False

def load():
	global PATRONS
	for user, rank in core.parameters.get('patrons').items():
		numeric = -1
		if rank.startswith('none'):
			numeric = TIER_NONE
		elif rank.startswith('constant'):
			numeric = TIER_CONSTANT
		elif rank.startswith('quadratic'):
			numeric = TIER_QUADRATIC
		elif rank.startswith('exponential'):
			numeric = TIER_EXPONENTIAL
		elif rank.startswith('special'):
			numeric = TIER_SPECIAL
		if numeric == -1:
			raise ValueError('"{}" is an invalid patreon rank'.format(rank))
		PATRONS[user] = numeric
	global loaded
	loaded = True

def tier(uid):
	if not loaded:
		load()
	return PATRONS.get(uid, TIER_NONE)
