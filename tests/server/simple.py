# -*- coding: utf-8 -*-


import os
import sys

sys.path.append(os.path.dirname(os.getcwd()))


class MyClass(object):

    def one(self):
        return 1

    def twice(self, n):
        return n * 2

    def arglen(self, *args, **kwargs):
        return len(args) + len(kwargs)


if __name__ == "__main__":
    import jsonrpyc

    rpc = jsonrpyc.RPC(MyClass())
