"""
Tests of the RPC functionality.
"""

from __future__ import annotations

__all__ = ["RPCTestCase"]

import contextlib
import json
import os
import subprocess
import time

import pytest

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
            assert isinstance(err, jsonrpyc.RPCInvalidParams)

        self.rpc("one", args=(27,), callback=cb)

        with pytest.raises(jsonrpyc.RPCInvalidParams):
            self.rpc("one", args=(27,), block=0.1)

    def test_internal_error(self):
        with pytest.raises(jsonrpyc.RPCInternalError):
            self.rpc("fail", block=0.1)

    def test_method_not_found(self):
        for method in ["unknown", "__private", "__init__", "one.__globals__"]:
            with pytest.raises(jsonrpyc.RPCMethodNotFound):
                self.rpc(method, block=0.1)

    def test_single_underscore_method(self):
        assert self.rpc("_protected", block=0.1) == "protected"

    def test_invalid_lines_keep_server_alive(self):
        assert self.p.stdin is not None
        self.p.stdin.write(b"not json\n[1, 2]\n")
        self.p.stdin.flush()
        assert self.rpc("one", block=0.1) == 1

    def test_timeout_cleanup(self):
        def cb(err, res):
            raise AssertionError("callback must not be called after timeout")

        with pytest.raises(TimeoutError):
            self.rpc("one", callback=cb, block=0.1, timeout=1e-9)
        assert not self.rpc._results
        assert not self.rpc._callbacks

    def test_close(self):
        self.rpc.close(timeout=1)
        assert not self.rpc.watchdog.is_alive()


class LocalRPCTestCase(TestCase):

    def test_notification_has_no_id(self):
        r, w = os.pipe()
        with os.fdopen(r, "rb") as rf, os.fdopen(w, "wb") as wf:
            rpc = jsonrpyc.RPC(stdin=rf, stdout=wf, watch=False)
            rpc("notify")
            assert json.loads(rf.readline()) == {
                "jsonrpc": "2.0",
                "method": "notify",
                "params": {"args": [], "kwargs": {}},
            }

    def test_parse_params(self):
        parse = jsonrpyc.RPC._parse_params
        assert parse(None) == ([], {})
        assert parse([1, 2]) == ([1, 2], {})
        assert parse({"a": 1}) == ([], {"a": 1})
        assert parse({"args": [1], "kwargs": {"b": 2}}) == ([1], {"b": 2})
        with pytest.raises(jsonrpyc.RPCInvalidParams):
            parse(1)
