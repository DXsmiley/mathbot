from mathbot import safe

def test_sprint_working(capsys):
    safe.sprint('Hello, world!')
    captured = capsys.readouterr()
    assert captured.out == 'Hello, world!\n'
    safe.sprint('One', end='')
    safe.sprint('Two')
    captured = capsys.readouterr()
    assert captured.out == 'OneTwo\n'
    safe.sprint('A', 'B', 'C')
    captured = capsys.readouterr()
    assert captured.out == 'A B C\n'

class ThrowOnPrint:
    def __repr__(self):
        raise Exception

def test_sprint_throwing():
    safe.sprint(ThrowOnPrint())
