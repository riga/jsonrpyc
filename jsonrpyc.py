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

__all__ = []


import json


ERRORS = {
    -32700: "Parse error",
    -32600: "Invalid Request",
    -32601: "Method not found",
    -32602: "Invalid params",
    -32603: "Internal error",
    -32000: "Server error"
}


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
    def check_params(cls, params, allow_empty=False):
        if allow_empty and params is None:
            return
        if not isinstance(params, (list, tuple)):
            raise TypeError("params must be a list or tuple, got %s (%s)" % (params, type(params)))

    @classmethod
    def check_code(cls, code):
        if not isinstance(code, int):
            raise TypeError("code must be an integer, got %s (%s)" % (id, type(id)))
        elif code not in ERRORS:
            raise KeyError("unknown code, got %s (%s)" % (code, type(code)))

    @classmethod
    def check_message(cls, message, allow_empty=False):
        if allow_empty and message is None:
            return
        if not isinstance(message, str):
            raise TypeError("message must be a string, got %s (%s)" % (message, type(message)))

    @classmethod
    def request(cls, method, id=None, params=None):
        cls.check_method(method)
        cls.check_id(id, allow_empty=True)
        cls.check_params(params, allow_empty=True)

        req = "{\"jsonrpc\":\"2.0\",\"method\":\"%s\"" % method

        if id is not None:
            req += ",\"id\":%d" % id

        if params is not None:
            req += ",\"params\":%s" % json.dumps(params)

        req += "}"

        return req

    @classmethod
    def response(cls, id, result):
        cls.check_id(id)

        res = "{\"jsonrpc\":\"2.0\",\"id\":%d,\"result\":%s}" % (id, json.dumps(result))

        return res

    @classmethod
    def error(cls, id, code, message=None, data=None):
        cls.check_id(id)
        cls.check_message(message, allow_empty=True)

        if message is None:
            message = ERRORS[code]

        err = "{\"code\":%d,\"message\":\"%s\"" % (code, message)

        if data is not None:
            err += ",\"data\":%s}" % json.dumps(data)
        else:
            err += "}"

        err = "{\"jsonrpc\":\"2.0\",\"id\":%d,\"error\":%s}" % (id, err)

        return err


class RPC(object):
    pass
