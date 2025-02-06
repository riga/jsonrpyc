# coding: utf-8

"""
Tests of the RPC functionality.
"""


import os
import unittest
from subprocess import Popen, PIPE
from time import sleep

import jsonrpyc


__all__ = ["RPCTestCase"]


class RPCTestCase(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(RPCTestCase, self).__init__(*args, **kwargs)

        cwd = os.path.dirname(os.path.abspath(__file__))
        self.p = Popen(["python", "server/simple.py", "start"], stdin=PIPE, stdout=PIPE, cwd=cwd)

        self.rpc = jsonrpyc.RPC(stdout=self.p.stdin, stdin=self.p.stdout)

    def __del__(self):
        try:
            self.p.stdin.close()
        except OSError:
            pass
        try:
            self.p.stdout.close()
        except OSError:
            pass
        self.p.terminate()
        self.p.wait()

    def test_orphan_exits(self):
        self.p.terminate()
        self.p.wait(timeout=1)
        for _ in range(5):
            if self.rpc.watchdog._stop.is_set():
                break
            sleep(0.05)
        self.assertTrue(self.rpc.watchdog._stop.is_set())

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
