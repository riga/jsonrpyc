# coding: utf-8

from __future__ import annotations

import sys
import json
import io
import time
import threading
from typing import Any, Callable

# package infos
from jsonrpyc.__meta__ import (  # noqa
    __doc__,
    __author__,
    __email__,
    __copyright__,
    __credits__,
    __contact__,
    __license__,
    __status__,
    __version__,
)


class Spec(object):
    """
    This class wraps methods that create JSON-RPC 2.0 compatible string representations of
    request, response and error objects. All methods are class members, so you might never want to
    create an instance of this class, but rather use the methods directly:

    .. code-block:: python

        Spec.request("my_method", 18)  # the id is optional
        # => '{"jsonrpc":"2.0","method":"my_method","id": 18}'

        Spec.response(18, "some_result")
        # => '{"jsonrpc":"2.0","id":18,"result":"some_result"}'

        Spec.error(18, -32603)
        # => '{"jsonrpc":"2.0","id":18,"error":{"code":-32603,"message":"Internal error"}}'
    """

    @classmethod
    def check_id(cls, id: str | int | None, allow_empty: bool = False) -> None:
        """
        Value check for *id* entries. When *allow_empty* is *True*, *id* is allowed to be *None*.
        Raises a *TypeError* when *id* is neither an integer nor a string.
        """
        if (id is not None or not allow_empty) and not isinstance(id, (int, str)):
            raise TypeError(f"id must be an integer or string, got {id} ({type(id)})")

    @classmethod
    def check_method(cls, method: str) -> None:
        """
        Value check for *method* entries. Raises a *TypeError* when *method* is not a string.
        """
        if not isinstance(method, str):
            raise TypeError(f"method must be a string, got {method} ({type(method)})")

    @classmethod
    def check_code(cls, code: int) -> None:
        """
        Value check for *code* entries. Raises a *TypeError* when *code* is not an integer, or a
        *KeyError* when there is no :py:class:`RPCError` subclass registered for that *code*.
        """
        if not isinstance(code, int):
            raise TypeError(f"code must be an integer, got {code} ({type(code)})")

        if not get_error(code):
            raise ValueError(f"unknown code, got {code} ({type(code)})")

    @classmethod
    def request(
        cls,
        method: str,
        id: str | int | None = None,
        params: dict[str, Any] | None = None,
    ) -> str:
        """
        Creates the string representation of a request that calls *method* with optional *params*
        which are encoded by ``json.dumps``. When *id* is *None*, the request is considered a
        notification.
        """
        try:
            cls.check_method(method)
            cls.check_id(id, allow_empty=True)
        except Exception as e:
            raise RPCInvalidRequest(str(e))

        # start building the request string
        req = f"{{\"jsonrpc\":\"2.0\",\"method\":\"{method}\""

        # add the id when given
        if id is not None:
            # encode string ids
            if isinstance(id, str):
                id = json.dumps(id)
            req += f",\"id\":{id}"

        # add parameters when given
        if params is not None:
            try:
                req += f",\"params\":{json.dumps(params)}"
            except Exception as e:
                raise RPCParseError(str(e))

        # end the request string
        req += "}"

        return req

    @classmethod
    def response(cls, id: str | int | None, result: Any) -> str:
        """
        Creates the string representation of a respone that was triggered by a request with *id*.
        A *result* is required, even if it is *None*.
        """
        try:
            cls.check_id(id)
        except Exception as e:
            raise RPCInvalidRequest(str(e))

        # encode string ids
        if isinstance(id, str):
            id = json.dumps(id)

        # build the response string
        try:
            res = f"{{\"jsonrpc\":\"2.0\",\"id\":{id},\"result\":{json.dumps(result)}}}"
        except Exception as e:
            raise RPCParseError(str(e))

        return res

    @classmethod
    def error(cls, id: str | int | None, code: int, data: dict | None = None) -> str:
        """
        Creates the string representation of an error that occured while processing a request with
        *id*. *code* must lead to a registered :py:class:`RPCError`. *data* might contain
        additional, detailed error information and is encoded by ``json.dumps`` when set.
        """
        try:
            cls.check_id(id)
            cls.check_code(code)
        except Exception as e:
            raise RPCInvalidRequest(str(e))

        # build the inner error data
        message = get_error(code).title
        err_data = f"{{\"code\":{code},\"message\":\"{message}\""

        # insert data when given
        if data is not None:
            try:
                err_data += f",\"data\":{json.dumps(data)}}}"
            except Exception as e:
                raise RPCParseError(str(e))
        else:
            err_data += "}"

        # encode string ids
        if isinstance(id, str):
            id = json.dumps(id)

        # start building the error string
        err = f"{{\"jsonrpc\":\"2.0\",\"id\":{id},\"error\":{err_data}}}"

        return err


class RPC(object):
    """
    The main class of *jsonrpyc*. Instances of this class wrap an input stream *stdin* and an output
    stream *stdout* in order to communicate with other services. A service is not even forced to be
    written in Python as long as it strictly implements the JSON-RPC 2.0 specification. RPC
    instances may wrap a *target* object. By means of a :py:class:`Watchdog` instance, incoming
    requests are routed to methods of this object whose result might be sent back as a response.
    The watchdog instance is created but not started yet, when *watch* is not *True*.
    Example implementation:

    *server.py*

    .. code-block:: python

        import jsonrpyc

        class MyTarget(object):

            def greet(self, name):
                return f"Hi, {name}!"

        jsonrpc.RPC(MyTarget())

    *client.py*

    .. code-block:: python

        import jsonrpyc
        from subprocess import Popen, PIPE

        p = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE)
        rpc = jsonrpyc.RPC(stdout=p.stdin, stdin=p.stdout)

        # non-blocking remote procedure call with callback and js-like signature
        def cb(err, res=None):
            if err:
                throw err
            print(f"callback got: {res}")

        rpc("greet", args=("John",), callback=cb)

        # cb is called asynchronously which prints
        # => "callback got: Hi, John!"

        # blocking remote procedure call with 0.1s polling
        print(rpc("greet", args=("John",), block=0.1))
        # => "Hi, John!"

        # shutdown the process
        p.stdin.close()
        p.stdout.close()
        p.terminate()
        p.wait()

    .. py:attribute:: target

        The wrapped target object. Might be *None* when no object is wrapped, e.g. for the *client*
        RPC instance.

    .. py:attribute:: stdin

        The input stream, re-opened with ``"rb"``.

    .. py:attribute:: stdout

        The output stream, re-opened with ``"wb"``.

    .. py:attribute:: watch

        The :py:class:`Watchdog` instance that optionally watches *stdin* and dispatches incoming
        requests.
    """

    EMPTY_RESULT = object()

    def __init__(
        self: RPC,
        target: Any | None = None,
        stdin: io.TextIOBase | None = None,
        stdout: io.TextIOBase | None = None,
        watch: bool = True,
        **kwargs,
    ) -> None:
        super().__init__()

        # the wrapped target object
        self.target = target

        # open streams
        stdin = sys.stdin if stdin is None else stdin
        stdout = sys.stdout if stdout is None else stdout
        self.stdin = io.open(stdin.fileno(), "rb")
        self.stdout = io.open(stdout.fileno(), "wb")

        # other attributes
        self._i = -1
        self._callbacks = {}
        self._results = {}

        # create and optionall start the watchdog
        kwargs["start"] = watch
        kwargs.setdefault("daemon", target is None)
        self.watchdog = Watchdog(self, **kwargs)

    def __del__(self: RPC) -> None:
        watchdog = getattr(self, "watchdog", None)
        if watchdog:
            watchdog.stop()

    def __call__(self: RPC, *args, **kwargs) -> None:
        """
        Shorthand for :py:meth:`call`.
        """
        return self.call(*args, **kwargs)

    def call(
        self: RPC,
        method: str,
        args: tuple[Any] = (),
        kwargs: dict | None = None,
        callback: Callable | None = None,
        block: int = 0,
    ) -> None:
        """
        Performs an actual remote procedure call by writing a request representation (a string) to
        the output stream. The remote RPC instance uses *method* to route to the actual method to
        call with *args* and *kwargs*. When *callback* is set, it will be called with the result of
        the remote call. When *block* is larger than *0*, the calling thread is blocked until the
        result is received. In this case, *block* will be the poll interval, emulating synchronuous
        return value behavior. When both *callback* is *None* and *block* is *0* or smaller, the
        request is considered a notification and the remote RPC instance will not send a response.
        """
        # default kwargs
        if kwargs is None:
            kwargs = {}

        # check if the call is a notification
        is_notification = callback is None and block <= 0

        # create a new id for requests expecting a response
        id = None
        if not is_notification:
            self._i += 1
            id = self._i

        # register the callback
        if callback is not None:
            self._callbacks[id] = callback

        # store an empty result for the meantime
        if block > 0:
            self._results[id] = self.EMPTY_RESULT

        # create the request
        params = {"args": args, "kwargs": kwargs}
        req = Spec.request(method, id=id, params=params)
        self._write(req)

        # blocking return value behavior
        if block > 0:
            while True:
                if self._results[id] != self.EMPTY_RESULT:
                    result = self._results[id]
                    del self._results[id]
                    if isinstance(result, Exception):
                        raise result
                    return result
                time.sleep(block)

    def _handle(self: RPC, line: str) -> None:
        """
        Handles an incoming *line* and dispatches the parsed object to the request, response, or
        error handlers.
        """
        obj = json.loads(line)

        # dispatch to the correct handler
        if "method" in obj:
            # request
            self._handle_request(obj)
        elif "error" not in obj:
            # response
            self._handle_response(obj)
        else:
            # error
            self._handle_error(obj)

    def _handle_request(self: RPC, req: dict[str, Any]) -> None:
        """
        Handles an incoming request *req*. When it containes an id, a response or error is sent
        back.
        """
        try:
            method = self._route(req["method"])
            result = method(*req["params"]["args"], **req["params"]["kwargs"])
            if "id" in req:
                res = Spec.response(req["id"], result)
                self._write(res)
        except Exception as e:
            if "id" in req:
                if isinstance(e, RPCError):
                    err = Spec.error(req["id"], e.code, e.data)
                else:
                    err = Spec.error(req["id"], -32603, str(e))
                self._write(err)

    def _handle_response(self: RPC, res: dict[str, Any]) -> None:
        """
        Handles an incoming successful response *res*. Blocking calls are resolved and registered
        callbacks are invoked with the first error argument being set to *None*.
        """
        # set the result
        if res["id"] in self._results:
            self._results[res["id"]] = res["result"]

        # lookup and invoke the callback
        if res["id"] in self._callbacks:
            callback = self._callbacks[res["id"]]
            del self._callbacks[res["id"]]
            callback(None, res["result"])

    def _handle_error(self: RPC, res: dict[str, Any]) -> None:
        """
        Handles an incoming failed response *res*. Blocking calls throw an exception and
        registered callbacks are invoked with an exception and the second result argument set to
        *None*.
        """
        # extract the error and create an actual error instance to raise
        err = res["error"]
        error = get_error(err["code"])(err.get("data", err["message"]))

        # set the error
        if res["id"] in self._results:
            self._results[res["id"]] = error

        # lookup and invoke the callback
        if res["id"] in self._callbacks:
            callback = self._callbacks[res["id"]]
            del self._callbacks[res["id"]]
            callback(error, None)

    def _route(self: RPC, method: str) -> Any:
        """
        Returnes the method of the wrapped target object to be called when *method* is requested.
        Example:

        .. code-block:: python

            MyClassB(object):
                def foo(self):
                    return 123

            MyClassA(object):
                def __init__(self):
                    self.b = MyClassB()

                def bar(self):
                    return "test"

            rpc = RPC(MyClassA())

            rpc._route("bar")
            # => <bound method MyClassA.bar ...>

            rpc._route("b.foo")
            # => <bound method MyClassB.foo ...>
        """
        # recursively traverse target attributes
        obj = self.target
        for part in method.split("."):
            if not hasattr(obj, part):
                break
            obj = getattr(obj, part)
        else:
            return obj

        raise RPCMethodNotFound(data=method)

    def _write(self: RPC, s: str) -> None:
        """
        Writes a string *s* to the output stream.
        """
        self.stdout.write(bytearray(s + "\n", "utf-8"))
        self.stdout.flush()


class Watchdog(threading.Thread):
    """
    This class represents a thread that watches the input stream of an :py:class:`RPC` instance for
    incoming content and dispatches requests to it.

    .. py:attribute:: rpc

        The :py:class:`RPC` instance.

    .. py:attribute:: name

        The thread's name.

    .. py:attribute:: interval

        The polling interval of the run loop.

    .. py:attribute:: daemon

        The thread's daemon flag.
    """

    def __init__(
        self: Watchdog,
        rpc: RPC,
        name: str = "watchdog",
        interval: float = 0.1,
        daemon: bool = False,
        start: bool = True,
    ) -> None:
        super().__init__()

        # store attributes
        self.rpc = rpc
        self.name = name
        self.interval = interval
        self.daemon = daemon

        # register a stop event
        self._stop = threading.Event()

        if start:
            self.start()

    def start(self: Watchdog) -> None:
        """
        Starts with thread's activity.
        """
        super().start()

    def stop(self: Watchdog) -> None:
        """
        Stops with thread's activity.
        """
        self._stop.set()

    def run(self: Watchdog) -> None:
        # reset the stop event
        self._stop.clear()

        # stop here when stdin is not set or closed
        if not self.rpc.stdin or self.rpc.stdin.closed:
            return

        # read new incoming lines
        last_pos = 0
        while not self._stop.is_set():
            lines = None

            # stop when stdin is closed
            if self.rpc.stdin.closed:
                break

            # read from stdin depending on whether it is a tty or not
            if self.rpc.stdin.isatty():
                cur_pos = self.rpc.stdin.tell()
                if cur_pos != last_pos:
                    self.rpc.stdin.seek(last_pos)
                    lines = self.rpc.stdin.readlines()
                    last_pos = self.rpc.stdin.tell()
                    self.rpc.stdin.seek(cur_pos)
            else:
                try:
                    lines = [self.rpc.stdin.readline()]
                except IOError:
                    # prevent residual race conditions occurring when stdin is closed externally
                    pass

            # handle new lines if any
            if lines:
                for line in lines:
                    line = line.decode("utf-8").strip()
                    if line:
                        self.rpc._handle(line)
            else:
                self._stop.wait(self.interval)


class RPCError(Exception):
    """
    Base class for RPC errors.

    .. py:attribute:: message

        The message of this error, i.e., ``"<title> (<code>)[, data: <data>]"``.

    .. py:attribute:: data

        Additional data of this error. Setting the data attribute will also change the message
        attribute.
    """

    def __init__(self: RPCError, data: str | None = None) -> None:
        # build the error message
        message = f"{self.title} ({self.code})"
        if data is not None:
            message += f", data: {data}"
        self.message = message

        super().__init__(message)

        self.data = data

    def __str__(self):
        return self.message


error_map_distinct = {}
error_map_range = {}


def is_range(code: Any) -> bool:
    return (
        isinstance(code, tuple) and
        len(code) == 2 and
        all(isinstance(i, int) for i in code) and
        code[0] < code[1]
    )


def register_error(cls: type) -> type:
    """
    Decorator that registers a new RPC error derived from :py:class:`RPCError`. The purpose of
    error registration is to have a mapping of error codes/code ranges to error classes for faster
    lookups during error creation.

    .. code-block:: python

        @register_error
        class MyCustomRPCError(RPCError):
            code = ...
            title = "My custom error"
    """
    # it would be much cleaner to add a meta class to RPCError as a registry for codes
    # but in CPython 2 exceptions aren't types, so simply provide a registry mechanism here
    if not issubclass(cls, RPCError):
        raise TypeError(f"'{cls}' is not a subclass of RPCError")

    code = cls.code

    if isinstance(code, int):
        error_map = error_map_distinct
    elif is_range(code):
        error_map = error_map_range
    else:
        raise TypeError(f"invalid RPC error code {code}")

    if code in error_map:
        raise AttributeError(f"duplicate RPC error code {code}")

    error_map[code] = cls

    return cls


def get_error(code: int) -> type | None:
    """
    Returns the RPC error class that was previously registered to *code*. *None* is returned when no
    class could be found.
    """
    if code in error_map_distinct:
        return error_map_distinct[code]

    for (lower, upper), cls in error_map_range.items():
        if lower <= code <= upper:
            return cls

    return None


@register_error
class RPCParseError(RPCError):

    code = -32700
    title = "Parse error"


@register_error
class RPCInvalidRequest(RPCError):

    code = -32600
    title = "Invalid Request"


@register_error
class RPCMethodNotFound(RPCError):

    code = -32601
    title = "Method not found"


@register_error
class RPCInvalidParams(RPCError):

    code = -32602
    title = "Invalid params"


@register_error
class RPCInternalError(RPCError):

    code = -32603
    title = "Internal error"


@register_error
class RPCServerError(RPCError):

    code = (-32099, -32000)
    title = "Server error"
