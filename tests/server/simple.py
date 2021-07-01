# coding: utf-8

"""
Simple script starting an RPC server and wraps a custom class.
"""

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


def start():
    import jsonrpyc
    jsonrpyc.RPC(MyClass())


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        start()
