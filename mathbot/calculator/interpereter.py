class Interpereter:

	def __init__(self):
		self.handlers = {}

	def


i = Interpereter()
@i.rule('binop')
def binop(ev, left, operator, right):
	left = ev(left)
	right = ev(right)
	
