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
    pass
