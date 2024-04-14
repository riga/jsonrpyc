<!-- marker-before-logo -->

<p align="center">
  <img src="https://media.githubusercontent.com/media/riga/jsonrpyc/master/assets/logo.png" width="400" />
</p>

<!-- marker-after-logo -->

<!-- marker-before-badges -->

<p align="center">
  <a href="http://jsonrpyc.readthedocs.io">
    <img alt="Documentation status" src="https://readthedocs.org/projects/jsonrpyc/badge/?version=latest" />
  </a>
  <img alt="Python version" src="https://img.shields.io/badge/Python-%E2%89%A53.8-blue" />
  <a href="https://pypi.python.org/pypi/jsonrpyc">
    <img alt="Package version" src="https://img.shields.io/pypi/v/jsonrpyc.svg?style=flat" />
  </a>
  <a href="https://codecov.io/gh/riga/jsonrpyc">
    <img alt="Code coverge" src="https://codecov.io/gh/riga/jsonrpyc/branch/master/graph/badge.svg?token=R8SY3O6KB9" />
  </a>
  <a href="https://github.com/riga/jsonrpyc/actions/workflows/lint_and_test.yml">
    <img alt="Build status" src="https://github.com/riga/jsonrpyc/actions/workflows/lint_and_test.yml/badge.svg" />
  </a>
  <a href="https://github.com/riga/jsonrpyc/blob/master/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/riga/jsonrpyc.svg" />
  </a>
</p>

<!-- marker-after-badges -->

<!-- marker-before-header -->

Minimal python RPC implementation based on the [JSON-RPC 2.0 specs](http://www.jsonrpc.org/specification).

Original source hosted at [GitHub](https://github.com/riga/jsonrpyc).

<!-- marker-after-header -->

<!-- marker-before-body -->

<!-- marker-before-usage -->

## Usage

``jsonrpyc.RPC`` instances basically wrap an input stream and an output stream in order to communicate with other *services*.
A service is not even forced to be written in Python as long as it strictly implements the JSON-RPC 2.0 specs.
A suitable implementation for NodeJs is [node-json-rpc](https://github.com/riga/node-json-rpc).
A ``jsonrpyc.RPC`` instance may wrap a *target* object.
Incomming requests will be routed to methods of this object whose result might be sent back as a response. Example implementation:


### ``server.py``

```python
import jsonrpyc

class MyTarget(object):

    def greet(self: MyTarget, name: str) -> str:
        return f"Hi, {name}!"

jsonrpyc.RPC(MyTarget())
```


### ``client.py``

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

def cb(err: Exception | None, res: str | None = None) -> None:
    if err:
        raise err
    print(f"callback got: {res}")

rpc("greet", args=("John",), callback=cb)

# cb is called asynchronously which prints
# => "callback got: Hi, John!"


#
# shutdown
#

p.stdin.close()
p.stdout.close()
p.terminate()
p.wait()
```

<!-- marker-after-usage -->

<!-- marker-before-info -->

## Installation

Install simply via [pip](https://pypi.python.org/pypi/jsonrpyc).

```bash
pip install jsonrpyc
```


## Contributing

If you like to contribute to jsonrpyc, I'm happy to receive pull requests.
Just make sure to add new test cases and run them via:

```bash
> pytest tests
```


## Development

- Source hosted at [GitHub](https://github.com/riga/jsonrpyc)
- Report issues, questions, feature requests on [GitHub Issues](https://github.com/riga/jsonrpyc/issues)

<!-- marker-after-info -->

<!-- marker-after-body -->
