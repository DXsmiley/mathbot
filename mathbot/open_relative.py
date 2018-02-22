import inspect
import os

def open_relative(filename, *args, **kwargs):
    codefile = inspect.stack()[1].filename
    abspath = os.path.abspath(codefile)
    directory = os.path.dirname(abspath)
    path = os.path.join(directory, filename)
    return open(path, *args, **kwargs)