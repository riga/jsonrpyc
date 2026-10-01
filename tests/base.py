from __future__ import annotations

import os
import sys
import unittest

# adjust the path to import jsonrpyc
this_dir = os.path.dirname(os.path.abspath(__file__))
repo_dir = os.path.normpath(os.path.dirname(this_dir))
sys.path.insert(0, os.path.join(repo_dir, "src"))


class TestCase(unittest.TestCase):
    """
    Base class for tests.
    """
