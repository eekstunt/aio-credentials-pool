import os
import sys

import pytest

tests_directory = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.dirname(tests_directory))


@pytest.fixture(scope='session')
def database_name() -> str:
    return 'test'
