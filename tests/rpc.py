# -*- coding: utf-8 -*-


import os
import time
from subprocess import Popen, PIPE

from .base import TestCase, jsonrpyc


__all__ = ["RPCTestCase"]


class RPCTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(RPCTestCase, self).__init__(*args, **kwargs)

        cwd = os.path.dirname(os.path.abspath(__file__))
        self.p = Popen(["python", "clients/simple.py"], stdin=PIPE, stdout=PIPE, cwd=cwd)

        self.rpc = jsonrpyc.RPC(stdout=self.p.stdin, stdin=self.p.stdout)

    def __del__(self):
        self.p.terminate()

    def test_request_wo_args(self):
        def cb(err, one):
            self.assertEqual(err, None)
            self.assertEqual(one, 1)
        self.rpc("one", callback=cb)

        self.assertEqual(self.rpc("one", block=0.1), 1)

    def test_request_w_args(self):
        def cb(err, twice):
            self.assertEqual(err, None)
            self.assertEqual(twice, 84)
        self.rpc("twice", args=(42,), callback=cb)

        self.assertEqual(self.rpc("twice", args=(42,), block=0.1), 84)

    def test_request_arguments(self):
        args = (1, None, True)
        kwargs = {"a": {}, "b": [1, 2]}

        def cb(err, n):
            self.assertEqual(err, None)
            self.assertEqual(n, 5)
        self.rpc("arglen", args=args, kwargs=kwargs, callback=cb)

        self.assertEqual(self.rpc("arglen", args=args, kwargs=kwargs, block=0.1), 5)

    def test_request_error(self):
        def cb(err, *args):
            self.assertIsInstance(err, jsonrpyc.RPCInternalError)
        self.rpc("one", args=(27,), callback=cb)

        err = None
        try:
            self.rpc("one", args=(27,), block=0.1)
        except Exception as e:
            err = e
        finally:
            self.assertIsInstance(err, jsonrpyc.RPCInternalError)
