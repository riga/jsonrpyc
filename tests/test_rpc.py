"""
Tests of the RPC functionality.
"""

from __future__ import annotations

__all__ = ["RPCTestCase"]

import contextlib
import os
import subprocess
import time

import jsonrpyc

from .base import TestCase


class RPCTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cwd = os.path.dirname(os.path.abspath(__file__))
        self.p = subprocess.Popen(
            ["python", "server/simple.py", "start"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=cwd,
        )

        self.rpc = jsonrpyc.RPC(stdout=self.p.stdin, stdin=self.p.stdout)

    def __del__(self):
        # guard fast deletion
        if getattr(self, "p", None) is None:
            return

        for stream in (self.p.stdin, self.p.stdout):
            if stream is not None:
                with contextlib.suppress(OSError):
                    stream.close()
        self.p.terminate()
        self.p.wait()

    def test_orphan_exits(self):
        self.p.terminate()
        self.p.wait(timeout=1)
        for _ in range(5):
            if self.rpc.watchdog._stop_event.is_set():
                break
            time.sleep(0.05)
        assert self.rpc.watchdog._stop_event.is_set()

    def test_request_wo_args(self):
        def cb(err, one):
            assert err is None
            assert one == 1

        self.rpc("one", callback=cb)

        assert self.rpc("one", block=0.1) == 1

    def test_request_w_args(self):
        def cb(err, twice):
            assert err is None
            assert twice == 84

        self.rpc("twice", args=(42,), callback=cb)

        assert self.rpc("twice", args=(42,), block=0.1) == 84

    def test_request_arguments(self):
        args = (1, None, True)
        kwargs = {"a": {}, "b": [1, 2]}

        def cb(err, n):
            assert err is None
            assert n == 5

        self.rpc("arglen", args=args, kwargs=kwargs, callback=cb)

        assert self.rpc("arglen", args=args, kwargs=kwargs, block=0.1) == 5

    def test_request_error(self):
        def cb(err, *args):
            assert isinstance(err, jsonrpyc.RPCInternalError)

        self.rpc("one", args=(27,), callback=cb)

        err = None
        try:
            self.rpc("one", args=(27,), block=0.1)
        except Exception as e:
            err = e
        finally:
            assert isinstance(err, jsonrpyc.RPCInternalError)
