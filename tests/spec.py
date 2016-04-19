# -*- coding: utf-8 -*-


from .base import TestCase, jsonrpyc as rpc


__all__ = ["SpecTestCase"]


class SpecTestCase(TestCase):

    def __init__(self, *args, **kwargs):
        super(SpecTestCase, self).__init__(*args, **kwargs)

    def test_request(self):
        req = rpc.Spec.request("some_method")
        self.assertEqual(req, '{"jsonrpc":"2.0","method":"some_method"}')

    def test_request_with_id(self):
        req = rpc.Spec.request("some_method", 18)
        self.assertEqual(req, '{"jsonrpc":"2.0","method":"some_method","id":18}')

    def test_request_with_params(self):
        req = rpc.Spec.request("some_method", params=[1, 2, True])
        self.assertEqual(req, '{"jsonrpc":"2.0","method":"some_method","params":[1, 2, true]}')

    def test_response(self):
        res = rpc.Spec.response(18, None)
        self.assertEqual(res, '{"jsonrpc":"2.0","id":18,"result":null}')

    def test_error(self):
        err = rpc.Spec.error(18, -32603)
        self.assertEqual(err, '{"jsonrpc":"2.0","id":18,"error":{"code":-32603,'
                              '"message":"Internal error"}}')

    def test_error_with_message(self):
        err = rpc.Spec.error(18, -32603, message="custom error")
        self.assertEqual(err, '{"jsonrpc":"2.0","id":18,"error":{"code":-32603,'
                              '"message":"custom error"}}')

    def test_error_with_data(self):
        err = rpc.Spec.error(18, -32603, data=[1, 2, True])
        self.assertEqual(err, '{"jsonrpc":"2.0","id":18,"error":{"code":-32603,'
                              '"message":"Internal error","data":[1, 2, true]}}')
