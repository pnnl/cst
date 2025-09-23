import sys
from pathlib import Path


def version():
    _version = Path("cosim_toolbox/_version.py").read_text()
    _version = _version.split("\"")[1]
    print(_version)

def cosim_toolbox():
    if sys.argv.__len__() == 2:
        if sys.argv[1] == "-v" or sys.argv[1] == "--version":
            version()
