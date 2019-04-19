
# -*- coding: utf-8 -*-


import os
from subprocess import Popen, PIPE
from distutils.core import setup
import jsonrpyc


readme = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
if os.path.isfile(readme):
    cmd = "pandoc --from=markdown --to=rst " + readme
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True, executable="/bin/bash")
    out, err = p.communicate()
    if p.returncode != 0:
        raise Exception("pandoc conversion failed: " + err)
    long_description = out.decode("utf-8")
else:
    long_description = ""

keywords = [
    "rpc", "json", "json-rpc", "2.0"
]

classifiers = [
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Development Status :: 4 - Beta",
    "Operating System :: OS Independent",
    "License :: OSI Approved :: MIT License",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Information Technology"
]


setup(
    name             = jsonrpyc.__name__,
    version          = jsonrpyc.__version__,
    author           = jsonrpyc.__author__,
    description      = jsonrpyc.__doc__.strip(),
    license          = jsonrpyc.__license__,
    url              = jsonrpyc.__contact__,
    py_modules       = [jsonrpyc.__name__],
    keywords         = keywords,
    classifiers      = classifiers,
    long_description = long_description,
    data_files       = ["LICENSE"]
)
