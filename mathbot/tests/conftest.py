import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--runautomata",
        action = "store_true",
        default = False,
        help = "Run tests reliant on the automata"
    )
