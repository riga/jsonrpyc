# -*- coding: utf-8 -*-

"""
Minimal python JSON-RPC 2.0 implementation in a single file.
"""


__author__     = "Marcel Rieger"
__copyright__  = "Copyright 2016, Marcel Rieger"
__credits__    = ["Marcel Rieger"]
__contact__    = "https://github.com/riga/jsonrpyc"
__license__    = "MIT"
__status__     = "Development"
__version__    = "0.0.1"

__all__ = ["RPC"]


import sys
import json
import time
import threading


class Spec(object):

    @classmethod
    def check_id(cls, id, allow_empty=False):
        if allow_empty and id is None:
            return
        if not isinstance(id, int):
            raise TypeError("id must be an integer, got %s (%s)" % (id, type(id)))

    @classmethod
    def check_method(cls, method):
        if not isinstance(method, str):
            raise TypeError("method must be a string, got %s (%s)" % (method, type(method)))

    @classmethod
    def check_code(cls, code):
        if not isinstance(code, int):
            raise TypeError("code must be an integer, got %s (%s)" % (id, type(id)))
        elif get_error(code) is None:
            raise KeyError("unknown code, got %s (%s)" % (code, type(code)))

    @classmethod
    def request(cls, method, id=None, params=None):
        try:
            cls.check_method(method)
            cls.check_id(id, allow_empty=True)
        except Exception as e:
            raise RPCInvalidRequest(e.message)

        req = "{\"jsonrpc\":\"2.0\",\"method\":\"%s\"" % method

        if id is not None:
            req += ",\"id\":%d" % id

        if params is not None:
            try:
                req += ",\"params\":%s" % json.dumps(params)
            except Exception as e:
                raise RPCParseError(e.message)

        req += "}"

        return req

    @classmethod
    def response(cls, id, result):
        try:
            cls.check_id(id)
        except Exception as e:
            raise RPCInvalidRequest(e.message)

        try:
            res = "{\"jsonrpc\":\"2.0\",\"id\":%d,\"result\":%s}" % (id, json.dumps(result))
        except Exception as e:
            raise RPCParseError(e.message)

        return res

    @classmethod
    def error(cls, id, code, data=None):
        try:
            cls.check_id(id)
            cls.check_code(code)
        except Exception as e:
            raise RPCInvalidRequest(e.message)

        message = get_error(code).title

        err = "{\"code\":%d,\"message\":\"%s\"" % (code, message)

        if data is not None:
            try:
                err += ",\"data\":%s}" % json.dumps(data)
            except Exception as e:
               raise RPCParseError(e.message)
        else:
            err += "}"

        err = "{\"jsonrpc\":\"2.0\",\"id\":%d,\"error\":%s}" % (id, err)

        return err


class RPC(object):

    EMPTY_RESULT = object()

    def __init__(self, target=None, stdin=None, stdout=None, **kwargs):
        super(RPC, self).__init__()

        self.target = target
        self.stdin = sys.stdin if stdin is None else stdin
        self.stdout = sys.stdout if stdout is None else stdout

        self._i = -1
        self._callbacks = {}
        self._results = {}

        kwargs.setdefault("daemon", target is None)
        self._watchdog = Watchdog(self, **kwargs)

    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)

    def call(self, method, args=(), kwargs=None, callback=None, block=0):
        if kwargs is None:
            kwargs = {}

        if callback is not None or block > 0:
            self._i += 1
            id = self._i
        else:
            id = None

        if callback is not None:
            self._callbacks[id] = callback

        if block > 0:
            self._results[id] = self.EMPTY_RESULT

        params = {"args": args, "kwargs": kwargs}
        req = Spec.request(method, id=id, params=params)
        self.stdout.write(req + "\n")
        self.stdout.flush()

        if block > 0:
            while True:
                if self._results[id] != self.EMPTY_RESULT:
                    result = self._results[id]
                    del self._results[id]
                    if isinstance(result, Exception):
                        raise result
                    else:
                        return result
                time.sleep(block)

    def _handle(self, line):
        obj = json.loads(line)

        # dispatch to the correct handler
        if "method" in obj:
            # request
            self._handle_request(obj)
        elif "error" not in obj:
            # response
            self._handle_response(obj)
        else:
            # error
            self._handle_error(obj)

    def _handle_request(self, req):
        try:
            method = self._route(req["method"])
            result = method(*req["params"]["args"], **req["params"]["kwargs"])
            if "id" in req:
                res = Spec.response(req["id"], result)
                self.stdout.write(res + "\n")
                self.stdout.flush()
        except Exception as e:
            if "id" in req:
                if isinstance(e, RPCError):
                    err = Spec.error(req["id"], e.code, e.data)
                else:
                    err = Spec.error(req["id"], -32603, e.message)
                self.stdout.write(err + "\n")
                self.stdout.flush()

    def _handle_response(self, res):
        if res["id"] in self._results:
            self._results[res["id"]] = res["result"]
        if res["id"] in self._callbacks:
            callback = self._callbacks[res["id"]]
            del self._callbacks[res["id"]]
            callback(None, res["result"])

    def _handle_error(self, res):
        err = res["error"]
        error = get_error(err["code"])(err.get("data", err["message"]))

        if res["id"] in self._results:
            self._results[res["id"]] = error
        if res["id"] in self._callbacks:
            callback = self._callbacks[res["id"]]
            del self._callbacks[res["id"]]
            callback(error, None)

    def _route(self, method):
        obj = self.target
        for part in method.split("."):
            if not hasattr(obj, part):
                break
            obj = getattr(obj, part)
        else:
            return obj
        raise RPCMethodNotFound(data=method)


class Watchdog(threading.Thread):

    def __init__(self, rpc, name=None, interval=0.1, daemon=False, start=True):
        super(Watchdog, self).__init__()

        self.rpc = rpc
        self.name = name
        self.interval = interval
        self.daemon = daemon

        self._stop = threading.Event()

        if start:
            self.start()

    def run(self):
        stream = self.rpc.stdin

        if stream.isatty():
            last_pos = 0
            while not self._stop.is_set():
                cur_pos = stream.tell()
                if cur_pos != last_pos:
                    stream.seek(last_pos)
                    lines = stream.readlines()
                    last_pos = stream.tell()
                    stream.seek(cur_pos)
                    for line in lines:
                        line = line.strip()
                        if line:
                            self.rpc._handle(line)
                else:
                    self._stop.wait(self.interval)
        else:
            while not self._stop.is_set():
                line = stream.readline().rstrip()
                if line:
                    self.rpc._handle(line)
                else:
                    self._stop.wait(self.interval)

    def stop(self):
        self._stop.set()


class RPCError(Exception):

    def __init__(self, data=None):
        message = "%s (%s)" % (self.title, self.code)
        if data is not None:
            message += ", data: " + str(data)

        super(RPCError, self).__init__(message)

        self.data = data


error_map_distinct = {}
error_map_range = {}


def is_range(code):
    return isinstance(code, tuple) and len(code) == 2 and all(isinstance(i, int) for i in code) \
           and code[0] < code[1]


def register_error(cls):
    # it would be much cleaner to add a meta class to RPCError as a registry for codes
    # but in cpython exceptions aren't types, so simply provide a registry mechanism here
    code = cls.code

    if isinstance(code, int):
        error_map = error_map_distinct
    elif is_range(code):
        error_map = error_map_range
    else:
        raise ValueError("invalid RPC error code " + str(code))

    if code in error_map:
        raise AttributeError("duplicate RPC error code " + str(code))

    error_map[code] = cls


def get_error(code):
    if code in error_map_distinct:
        return error_map_distinct[code]

    for (lower, upper), cls in error_map_range.items():
        if lower <= code <= upper:
            return cls

    return None


@register_error
class RPCParseError(RPCError):

    code = -32700
    title = "Parse error"


@register_error
class RPCInvalidRequest(RPCError):

    code = -32600
    title = "Invalid Request"


@register_error
class RPCMethodNotFound(RPCError):

    code = -32601
    title = "Method not found"


@register_error
class RPCInvalidParams(RPCError):

    code = -32602
    title = "Invalid params"


@register_error
class RPCInternalError(RPCError):

    code = -32603
    title = "Internal error"


@register_error
class RPCServerError(RPCError):

    code = (-32099, -32000)
    title = "Server error"
