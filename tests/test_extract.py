import os
import tempfile
import shutil

import pytest

from gen.parsers import extract_implementation


@pytest.fixture
def temp_directory():
    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()

    # Write some sample source code files to the directory
    file1_path = os.path.join(test_dir, "file1.py")
    with open(file1_path, "w") as f:
        f.write(
            """
class Foo:
    def __init__(self, x):
        self.x = x

class Bar:
    def __init__(self, y):
        self.y = y
        """
        )
    file2_path = os.path.join(test_dir, "file2.py")
    with open(file2_path, "w") as f:
        f.write(
            """
class Foo:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        """
        )

    yield test_dir

    # Remove the temporary directory and its contents
    shutil.rmtree(test_dir)


def test_extract_implementation(temp_directory):
    # Test that the function correctly extracts the implementations of each type
    type_impls = extract_implementation(temp_directory)
    assert type_impls == {
        "Foo": [
            "class Foo:\n    def __init__(self, x, y):\n        self.x = x\n        self.y = y\n",
            "class Foo:\n    def __init__(self, x):\n        self.x = x\n",
        ],
        "Bar": ["class Bar:\n    def __init__(self, y):\n        self.y = y\n"],
    }
