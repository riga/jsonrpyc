<!-- marker-before-logo -->

<p align="center">
  <a href="https://github.com/riga/jsonrpyc">
    <img alt="jsonrpyc logo" src="https://media.githubusercontent.com/media/riga/jsonrpyc/master/assets/logo.png" width="400" />
  </a>
</p>

<!-- marker-after-logo -->

<!-- marker-before-badges -->

<p align="center">
  <a href="http://jsonrpyc.readthedocs.io/en/latest">
    <img alt="Documentation status" src="https://readthedocs.org/projects/jsonrpyc/badge/?version=latest" />
  </a>
  <a href="https://github.com/riga/jsonrpyc/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/riga/jsonrpyc/actions/workflows/ci.yml/badge.svg" />
  </a>
  <img alt="Python version" src="https://img.shields.io/badge/Python-%E2%89%A53.9-blue" />
  <a href="https://pypi.python.org/pypi/jsonrpyc">
    <img alt="Package version" src="https://img.shields.io/pypi/v/jsonrpyc.svg?style=flat" />
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

class MyTarget:

    def greet(self, name: str) -> str:
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

# or with optional dev dependencies
pip install jsonrpyc[dev]
```

## Contributing

If you like to contribute to jsonrpyc, I'm happy to receive pull requests.

The full testing pipeline is based on [pre-commit](https://pre-commit.com).
Run the following to install development dependencies and set it up:

```shell
# inside the cloned repository
git lfs install
pip install -e .[dev]
pre-commit install
```

Now, every time you make a commit, the pre-commit and pre-push hooks will automatically run linting, type checking and unit tests.
To run them manually, use

```shell
# for linting, type checking and additional checks on all files
pre-commit run --all-files

# only for staged files
pre-commit run --all-files

# for unit tests
pytest
```

## Development

- Source hosted at [GitHub](https://github.com/riga/jsonrpyc)
- Report issues, questions, feature requests on [GitHub Issues](https://github.com/riga/jsonrpyc/issues)

<!-- marker-after-info -->

<!-- marker-after-body -->
