import abc

class Evaluable(abc.ABC):

	@abc.abstractmethod
	def eval(self, environment):
		pass

	@abc.abstractmethod
	def fulleval(self, environment):
		pass
