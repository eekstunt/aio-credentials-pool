import sys
from pathlib import Path

import pytest

tests_directory = Path(__file__).resolve().parent
sys.path.insert(0, str(tests_directory.parent))


@pytest.fixture(scope='session')
def database_name() -> str:
    return 'test'
