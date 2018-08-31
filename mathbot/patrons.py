TIER_NONE = 0
TIER_CONSTANT = 1
TIER_QUADRATIC = 2
TIER_EXPONENTIAL = 3
TIER_SPECIAL = 4

class InvalidPatronRankError(Exception):
	pass

class PatronageMixin:

	def patron_tier(self, uid):
		if not isinstance(uid, (str, int)):
			raise TypeError('User ID looks invalid')
		rank_string = self.parameters.get('patrons').get(str(uid))
		if rank_string is None:
			return TIER_NONE
		elif rank_string.startswith('constant'):
			return TIER_CONSTANT
		elif rank_string.startswith('quadratic'):
			return TIER_QUADRATIC
		elif rank_string.startswith('exponential'):
			return TIER_EXPONENTIAL
		elif rank_string.startswith('special'):
			return TIER_SPECIAL
		raise InvalidPatronRankError