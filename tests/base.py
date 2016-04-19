# -*- coding: utf-8 -*-


import os
import sys
import unittest


# adjust the path to import jsonrpyc
base = os.path.normpath(os.path.join(os.path.abspath(__file__), "../.."))
sys.path.append(base)
import jsonrpyc


class TestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestCase, self).__init__(*args, **kwargs)
