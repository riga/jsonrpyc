# -*- coding: utf-8 -*-


from base import jsonrpyc


class MyClass(object):

    def one(self):
        return 1

    def twice(self, n):
        return n * 2

    def arglen(self, *args, **kwargs):
        return len(args) + len(kwargs)


if __name__ == "__main__":
    rpc = jsonrpyc.RPC(MyClass())
