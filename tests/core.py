# -*- coding: utf-8 -*-


from .base import TestCase, jsonrpyc as rpc


__all__ = ["CoreTestCase"]


class CoreTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(CoreTestCase, self).__init__(*args, **kwargs)

    def test_trivial(self):
        self.assertEqual(1, 1)
