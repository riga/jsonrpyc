<img src="https://raw.githubusercontent.com/riga/jsonrpyc/master/logo.png" alt="jsonrpyc logo" width="250"/>
-

[![Build Status](https://travis-ci.org/riga/jsonrpyc.svg?branch=master)](https://travis-ci.org/riga/jsonrpyc) [![Documentation Status](https://readthedocs.org/projects/jsonrpyc/badge/?version=latest)](http://jsonrpyc.readthedocs.org/en/latest/?badge=latest)

Minimal python RPC implementation in a single file based on the [JSON-RPC 2.0 specs](http://www.jsonrpc.org/specification).


## Usage

``jsonrpyc.RPC`` instances basically wrap an input stream and an output stream in order to communicate with other *services*. A service is not even forced to be written in Python as long as it strictly implements the JSON-RPC 2.0 specs. A suitable implementation for NodeJs is [node-json-rpc](https://github.com/riga/node-json-rpc). A ``jsonrpyc.RPC`` instance may wrap a *target* object. Incomming requests will be routed to methods of this object whose result might be sent back as a response. Example implementation:


##### ``server.py``

```python
import jsonrpyc

class MyTarget(object):

    def greet(self, name):
    return "Hi, %s!" % name

jsonrpc.RPC(MyTarget())
```


##### ``async_client.py``

```python
import jsonrpyc
from subprocess import Popen, PIPE

p = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE)
rpc = jsonrpyc.RPC(stdout=p.stdin, stdin=p.stdout)

def cb(err, res=None):
    if err:
        throw err
    print("callback got: " + res)
rpc("greet", args=("John",))
# cb is called asynchronously which prints
# => "callback got: Hi, John!"
```


##### ``sync_client.py``

```python
import jsonrpyc
from subprocess import Popen, PIPE

p = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE)
rpc = jsonrpyc.RPC(stdout=p.stdin, stdin=p.stdout)

print(rpc("greet", args=("John",), block=0.1))
# => "Hi, John!"
```


## Installation and dependencies

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


## Authors

- [Marcel R.](https://github.com/riga)


## License

The MIT License (MIT)

Copyright (c) 2016 Marcel R.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
