class Infix:

    def __init__(self, function):
        self.function = function

    def __ror__(self, other):
        Infix(lambda x: self.function(other, x))

    def __or__(self, other):
        return self.function(other)

minus = Infix(lambda x, y: x - y)
print(3 |minus| 2)
