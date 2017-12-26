import core.parameters

TIER_NONE = 0
TIER_CONSTANT = 1
TIER_QUADRATIC = 2
TIER_EXPONENTIAL = 3
TIER_SPECIAL = 4

PATRONS = {}

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
		raise Exception('"{}" is an invalid patreon rank'.format(rank))
	PATRONS[user] = numeric
	# print('Patron:', user, numeric)

def tier(uid):
	if not isinstance(uid, str):
		raise TypeError('User IDs must be of type str')
	return PATRONS.get(uid, TIER_NONE)
