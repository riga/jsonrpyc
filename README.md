<img src="https://raw.githubusercontent.com/riga/jsonrpyc/master/logo.png" alt="jsonrpyc logo" width="250"/>

[![Build Status](https://travis-ci.org/riga/jsonrpyc.svg?branch=master)](https://travis-ci.org/riga/jsonrpyc) [![Documentation Status](https://readthedocs.org/projects/jsonrpyc/badge/?version=latest)](http://jsonrpyc.readthedocs.org/en/latest/?badge=latest) [![Package Status](https://img.shields.io/pypi/v/jsonrpyc.svg?style=flat)](https://pypi.python.org/pypi/jsonrpyc) [![License](https://img.shields.io/github/license/riga/jsonrpyc.svg)](https://github.com/riga/jsonrpyc/blob/master/LICENSE)


Minimal python RPC implementation in a single file based on the [JSON-RPC 2.0 specs](http://www.jsonrpc.org/specification).


## Usage

``jsonrpyc.RPC`` instances basically wrap an input stream and an output stream in order to communicate with other *services*. A service is not even forced to be written in Python as long as it strictly implements the JSON-RPC 2.0 specs. A suitable implementation for NodeJs is [node-json-rpc](https://github.com/riga/node-json-rpc). A ``jsonrpyc.RPC`` instance may wrap a *target* object. Incomming requests will be routed to methods of this object whose result might be sent back as a response. Example implementation:


##### ``server.py``

```python
import jsonrpyc

class MyTarget(object):

    def greet(self, name):
        return "Hi, %s!" % name

jsonrpyc.RPC(MyTarget())
```


##### ``client.py``

```python
import jsonrpyc
from subprocess import Popen, PIPE

p = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE)
rpc = jsonrpyc.RPC(stdout=p.stdin, stdin=p.stdout)

#
# sync usage
#

print(rpc("greet", args=("John",), block=0.1))
# => "Hi, John!"


#
# async usage
#

def cb(err, res=None):
    if err:
        raise err
    print("callback got: " + res)

rpc("greet", args=("John",), callback=cb)

# cb is called asynchronously which prints
# => "callback got: Hi, John!"
```


## Installation

Via [pip](https://pypi.python.org/pypi/jsonrpyc)

```bash
pip install jsonrpyc
```

or by simply copying the file into your project.


## Contributing

If you like to contribute to jsonrpyc, I'm happy to receive pull requests. Just make sure to add a new test cases and run them via:

```bash
> python -m unittest tests
```


## Development

- Source hosted at [GitHub](https://github.com/riga/jsonrpyc)
- Report issues, questions, feature requests on [GitHub Issues](https://github.com/riga/jsonrpyc/issues)
