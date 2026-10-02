from __future__ import annotations

__all__: list[str] = [
    "RPC",
    "RPCError",
    "RPCInternalError",
    "RPCInvalidParams",
    "RPCInvalidRequest",
    "RPCMethodNotFound",
    "RPCParseError",
    "RPCServerError",
    "Spec",
    "Watchdog",
    "register_error",
]

import inspect
import json
import logging
import os
import select
import sys
import threading
import time
from collections.abc import Callable
from typing import Any, Optional, Protocol

try:
    from typing import TypeAlias
except ImportError:
    from typing_extensions import TypeAlias  # ruff: ignore[deprecated-import]

# package infos
from jsonrpyc.__meta__ import (  # ruff: ignore[unused-import]
    __author__,
    __contact__,
    __copyright__,
    __credits__,
    __doc__,
    __email__,
    __license__,
    __status__,
    __version__,
)

Callback: TypeAlias = Callable[[Optional[Exception], Any], None]  # ruff: ignore[non-pep604-annotation-optional]

logger = logging.getLogger(__name__)

# pipes are not selectable on windows
_can_select = sys.platform != "win32"


class InputStream(Protocol):

    def fileno(self) -> int:
        ...

    @property
    def closed(self) -> bool:
        ...


class OutputStream(Protocol):

    def fileno(self) -> int:
        ...


class Spec:
    """
    This class wraps methods that create JSON-RPC 2.0 compatible string representations of request, response and error
    objects. All methods are class members, so you might never want to create an instance of this class, but rather use
    the methods directly:

    .. code-block:: python

        Spec.request("my_method", 18)  # the id is optional
        # => '{"jsonrpc":"2.0","method":"my_method","id":18}'

        Spec.response(18, "some_result")
        # => '{"jsonrpc":"2.0","id":18,"result":"some_result"}'

        Spec.error(18, -32603)
        # => '{"jsonrpc":"2.0","id":18,"error":{"code":-32603,"message":"Internal error"}}'
    """

    @classmethod
    def check_id(cls, id: str | int | None, *, allow_empty: bool = False) -> None:
        """
        Value check for *id* entries. When *allow_empty* is *True*, *id* is allowed to be *None*. Raises a *TypeError*
        when *id* is neither an integer nor a string (booleans are rejected as well).

        :param id: The id to check.
        :param allow_empty: Whether *id* is allowed to be *None*.
        :return: None.
        :raises TypeError: When *id* is invalid.
        """
        if id is None and allow_empty:
            return
        if isinstance(id, bool) or not isinstance(id, (int, str)):
            raise TypeError(f"id must be an integer or string, got {id} ({type(id)})")

    @classmethod
    def check_method(cls, method: str, /) -> None:
        """
        Value check for *method* entries. Raises a *TypeError* when *method* is not a string.

        :param method: The method to check.
        :return: None.
        :raises TypeError: When *method* is invalid.
        """
        if not isinstance(method, str):
            raise TypeError(f"method must be a string, got {method} ({type(method)})")

    @classmethod
    def check_code(cls, code: int, /) -> None:
        """
        Value check for *code* entries. Raises a *TypeError* when *code* is not an integer or when there is no
        :py:class:`RPCError` subclass registered for that *code*.

        :param code: The error code to check.
        :return: None.
        :raises TypeError: When *code* is invalid.
        """
        try:
            get_error(code)
        except Exception as e:
            raise TypeError(f"invalid error code, got {code} ({type(code)})") from e

    @classmethod
    def request(
        cls,
        method: str,
        id: str | int | None = None,
        *,
        params: Any = None,
    ) -> str:
        """
        Creates the string representation of a request that calls *method* with optional *params* which are encoded by
        ``json.dumps``. When *id* is *None*, the request is considered a notification.

        :param method: The method to call.
        :param id: The id of the request.
        :param params: The parameters of the request.
        :return: The request string.
        :raises RPCInvalidRequest: When *method* or *id* are invalid.
        :raises RPCParseError: When *params* could not be encoded.
        """
        try:
            cls.check_method(method)
            cls.check_id(id, allow_empty=True)
        except Exception as e:
            raise RPCInvalidRequest(str(e)) from e

        # start building the request string
        req = f"{{\"jsonrpc\":\"2.0\",\"method\":{json.dumps(method)}"

        # add the id when given
        if id is not None:
            req += f",\"id\":{json.dumps(id)}"

        # add parameters when given
        if params is not None:
            try:
                req += f",\"params\":{json.dumps(params)}"
            except Exception as e:
                raise RPCParseError(str(e)) from e

        # end the request string
        req += "}"

        return req

    @classmethod
    def response(cls, id: str | int | None, result: Any, /) -> str:
        """
        Creates the string representation of a response that was triggered by a request with *id*. A *result* is
        required, even if it is *None*.

        :param id: The id of the request that triggered this response.
        :param result: The result of the request.
        :return: The response string.
        :raises RPCInvalidRequest: When *id* is invalid.
        :raises RPCParseError: When *result* could not be encoded.
        """
        try:
            cls.check_id(id)
        except Exception as e:
            raise RPCInvalidRequest(str(e)) from e

        # build the response string
        try:
            res = f"{{\"jsonrpc\":\"2.0\",\"id\":{json.dumps(id)},\"result\":{json.dumps(result)}}}"
        except Exception as e:
            raise RPCParseError(str(e)) from e

        return res

    @classmethod
    def error(
        cls,
        id: str | int | None,
        code: int,
        *,
        data: Any | None = None,
    ) -> str:
        """
        Creates the string representation of an error that occurred while processing a request with *id*. *id* might be
        *None* when the id of the request could not be determined, e.g. for parse errors. *code* must lead to a
        registered :py:class:`RPCError`. *data* might contain additional, detailed error information and is encoded by
        ``json.dumps`` when set.

        :param id: The id of the request that triggered this error.
        :param code: The error code.
        :param data: Additional error data.
        :return: The error string.
        :raises RPCInvalidRequest: When *id* or *code* are invalid.
        :raises RPCParseError: When *data* could not be encoded.
        """
        try:
            cls.check_id(id, allow_empty=True)
            cls.check_code(code)
        except Exception as e:
            raise RPCInvalidRequest(str(e)) from e

        # build the inner error data
        message = get_error(code).title  # type: ignore[union-attr]
        err_data = f"{{\"code\":{code},\"message\":{json.dumps(message)}"

        # insert data when given
        if data is not None:
            try:
                err_data += f",\"data\":{json.dumps(data)}}}"
            except Exception as e:
                raise RPCParseError(str(e)) from e
        else:
            err_data += "}"

        # build the error string
        err = f"{{\"jsonrpc\":\"2.0\",\"id\":{json.dumps(id)},\"error\":{err_data}}}"

        return err


class RPC:
    """
    The main class of *jsonrpyc*. Instances of this class wrap an input stream *stdin* and an output stream *stdout* in
    order to communicate with other services. A service is not even forced to be written in Python as long as it
    strictly implements the JSON-RPC 2.0 specification. RPC instances may wrap a *target* object. By means of a
    :py:class:`Watchdog` instance, incoming requests are routed to methods of this object whose result might be sent
    back as a response. The watchdog instance is created but not started yet, when *watch* is not *True*.

    :param target: The target object to wrap.
    :param stdin: The input stream.
    :param stdout: The output stream.
    :param watch: Whether to start the watchdog.
    :param watch_kwargs: Additional keyword arguments for the watchdog.

    Example implementation:

    *server.py*

    .. code-block:: python

        import jsonrpyc

        class MyTarget(object):

            def greet(self, name):
                return f"Hi, {name}!"

        jsonrpyc.RPC(MyTarget())

    *client.py*

    .. code-block:: python

        import jsonrpyc
        from subprocess import Popen, PIPE

        p = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE)
        rpc = jsonrpyc.RPC(stdout=p.stdin, stdin=p.stdout)

        # non-blocking remote procedure call with callback and js-like signature
        def cb(err, res=None):
            if err:
                raise err
            print(f"callback got: {res}")

        rpc("greet", args=("John",), callback=cb)

        # cb is called asynchronously which prints
        # => "callback got: Hi, John!"

        # blocking remote procedure call with 0.1s polling
        print(rpc("greet", args=("John",), block=0.1))
        # => "Hi, John!"

        # shutdown the rpc and the process
        rpc.close()
        p.stdin.close()
        p.stdout.close()
        p.terminate()
        p.wait()

    .. py:attribute:: target

        The wrapped target object. Might be *None* when no object is wrapped, e.g. for the *client* RPC instance.

    .. py:attribute:: stdin

        The input stream, re-opened with ``"rb"``.

    .. py:attribute:: stdout

        The output stream, re-opened with ``"wb"``.

    .. py:attribute:: watch

        The :py:class:`Watchdog` instance that optionally watches *stdin* and dispatches incoming requests.

    Instances can be used as context managers, calling :py:meth:`close` on exit.
    """

    EMPTY_RESULT = object()

    def __init__(
        self,
        target: Any | None = None,
        stdin: InputStream | None = None,
        stdout: OutputStream | None = None,
        *,
        watch: bool = True,
        watch_kwargs: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()

        # the wrapped target object
        self.target = target

        # open input stream
        if stdin is None:
            stdin = sys.stdin
        self.original_stdin = stdin
        # the descriptor is owned by the original stream, so do not close it when this object is collected
        self.stdin = open(stdin.fileno(), "rb", closefd=False)

        # open output stream
        if stdout is None:
            stdout = sys.stdout
        self.original_stdout = stdout
        self.stdout = open(stdout.fileno(), "wb", closefd=False)

        # other attributes
        self._i = -1
        self._callbacks: dict[int, Callback] = {}
        self._results: dict[int, Any] = {}

        # locks guarding the id counter and registries, and writes to the output stream
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()

        # create and optionally start the watchdog
        watch_kwargs = dict(watch_kwargs or {})
        watch_kwargs["start"] = watch
        watch_kwargs.setdefault("daemon", target is None)
        self.watchdog = Watchdog(self, **watch_kwargs)

    def __del__(self) -> None:
        watchdog = getattr(self, "watchdog", None)
        if watchdog:
            watchdog.stop()

    def __enter__(self) -> RPC:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self, timeout: float | None = None) -> None:
        """
        Stops the watchdog and waits for it to finish for at most *timeout* seconds (indefinitely when *None*). On
        Windows, a watchdog that is waiting for input only finishes once new content or EOF is received, so passing a
        *timeout* is recommended there.

        :param timeout: The maximum time in seconds to wait for the watchdog to finish.
        :return: None.
        """
        self.watchdog.stop()
        if self.watchdog.is_alive() and self.watchdog is not threading.current_thread():
            self.watchdog.join(timeout)

    def __call__(
        self,
        method: str,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        *,
        callback: Callback | None = None,
        block: float = 0,
        timeout: float = 0,
    ) -> Any:
        """
        Shorthand for :py:meth:`call`.
        """
        return self.call(
            method,
            args=args,
            kwargs=kwargs,
            callback=callback,
            block=block,
            timeout=timeout,
        )

    def call(
        self,
        method: str,
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        *,
        callback: Callback | None = None,
        block: float = 0,
        timeout: float = 0,
    ) -> Any:
        """
        Performs an actual remote procedure call by writing a request representation (a string) to the output stream.
        The remote RPC instance uses *method* to route to the actual method to call with *args* and *kwargs*.

        When *callback* is set, it will be called with the result of the remote call. When *block* is larger than *0*,
        the calling thread is blocked until the result is received. In this case, *block* will be the poll interval,
        emulating synchronous return value behavior. When both *callback* is *None* and *block* is *0* or smaller, the
        request is considered a notification and the remote RPC instance will not send a response.

        If *timeout* is not zero, raise TimeoutError after *timeout* seconds with no response.

        :param method: The method to call.
        :param args: The positional arguments of the method.
        :param kwargs: The keyword arguments of the method.
        :param callback: The callback function.
        :param block: The poll interval in seconds.
        :param timeout: The timeout in seconds.
        :return: None if block is non-positive, otherwise the result of the remote call.
        :raises TimeoutError: When the request times out.
        """
        starting_time = time.monotonic()

        # default kwargs
        if kwargs is None:
            kwargs = {}

        # check if the call is a notification
        is_notification = callback is None and block <= 0

        # notifications have no id, all other requests get a new one
        if is_notification:
            req = Spec.request(method, params={"args": args, "kwargs": kwargs})
            self._write(req)
            return None

        with self._lock:
            self._i += 1
            id = self._i

            # register the callback
            if callback is not None:
                self._callbacks[id] = callback

            # store an empty result for the meantime
            if block > 0:
                self._results[id] = self.EMPTY_RESULT

        try:
            # create and send the request
            req = Spec.request(method, id=id, params={"args": args, "kwargs": kwargs})
            self._write(req)

            # non-blocking behavior
            if block <= 0:
                return None

            # blocking return value behavior
            while True:
                result = self._results[id]
                if result is not self.EMPTY_RESULT:
                    if isinstance(result, Exception):
                        raise result
                    return result

                if timeout and time.monotonic() - starting_time > timeout:
                    raise TimeoutError("RPC request timed out")

                time.sleep(block)

        except BaseException:
            # the response will not be awaited anymore
            with self._lock:
                self._callbacks.pop(id, None)
            raise

        finally:
            with self._lock:
                self._results.pop(id, None)

    def _handle(self, line: str) -> None:
        """
        Handles an incoming *line* and dispatches the parsed object to the request, response, or error handlers. Lines
        that cannot be parsed or that do not contain a JSON object are answered with an error whose id is *null*.

        :param line: The incoming line.
        :return: None.
        """
        try:
            obj = json.loads(line)
        except ValueError as e:
            self._write(Spec.error(None, RPCParseError.code, data=str(e)))
            return

        # dispatch to the correct handler
        if not isinstance(obj, dict):
            self._write(Spec.error(None, RPCInvalidRequest.code, data="expected a JSON object"))
        elif "method" in obj:
            # request
            self._handle_request(obj)
        elif "result" in obj:
            # response
            self._handle_response(obj)
        elif "error" in obj:
            # error
            self._handle_error(obj)
        else:
            logger.warning(f"ignoring invalid JSON-RPC object: {line}")

    @classmethod
    def _parse_params(cls, params: Any) -> tuple[list[Any], dict[str, Any]]:
        """
        Converts the *params* of an incoming request into positional and keyword arguments. Besides the
        ``{"args": [...], "kwargs": {...}}`` format used by jsonrpyc, plain lists (positional arguments) and objects
        (keyword arguments) as well as missing parameters are supported for compatibility with other implementations.

        :param params: The parameters of the request.
        :return: A tuple of positional and keyword arguments.
        :raises RPCInvalidParams: When *params* is neither a list nor a dictionary.
        """
        if params is None:
            return [], {}
        if isinstance(params, list):
            return params, {}
        if isinstance(params, dict):
            if (
                set(params) == {"args", "kwargs"} and
                isinstance(params["args"], list) and
                isinstance(params["kwargs"], dict)
            ):
                return params["args"], params["kwargs"]
            return [], params
        raise RPCInvalidParams(data=f"params must be a list or an object, got {params!r}")

    def _handle_request(self, req: dict[str, Any]) -> None:
        """
        Handles an incoming request *req*. When it contains an id, a response or error is sent back.

        :param req: The incoming request.
        :return: None.
        """
        try:
            if not isinstance(req["method"], str):
                raise RPCInvalidRequest(data=f"method must be a string, got {req['method']!r}")
            method = self._route(req["method"])
            args, kwargs = self._parse_params(req.get("params"))

            # check if the arguments match the signature to distinguish invalid params from internal errors
            try:
                signature = inspect.signature(method)
            except (TypeError, ValueError):
                pass
            else:
                try:
                    signature.bind(*args, **kwargs)
                except TypeError as e:
                    raise RPCInvalidParams(data=str(e)) from e

            result = method(*args, **kwargs)
            if "id" in req:
                res = Spec.response(req["id"], result)
                self._write(res)
        except Exception as e:
            if "id" in req:
                if isinstance(e, RPCError):
                    err = Spec.error(req["id"], e.code, data=e.data)
                else:
                    err = Spec.error(req["id"], -32603, data=str(e))
                self._write(err)

    def _handle_response(self, res: dict[str, Any]) -> None:
        """
        Handles an incoming successful response *res*. Blocking calls are resolved and registered callbacks are invoked
        with the first error argument being set to *None*.

        :param res: The incoming response.
        :return: None.
        """
        # set the result and lookup the callback
        with self._lock:
            if res["id"] in self._results:
                self._results[res["id"]] = res["result"]
            callback = self._callbacks.pop(res["id"], None)

        # invoke the callback
        if callback is not None:
            callback(None, res["result"])

    def _handle_error(self, res: dict[str, Any]) -> None:
        """
        Handles an incoming failed response *res*. Blocking calls throw an exception and registered callbacks are
        invoked with an exception and the second result argument set to *None*.

        :param res: The incoming error response.
        :return: None.
        """
        # extract the error and create an actual error instance to raise
        err = res["error"]
        data = err.get("data", err.get("message"))
        try:
            error = get_error(err["code"])(data)
        except (TypeError, ValueError):
            # fallback for codes without registered error class, e.g. application-defined ones
            error = RPCError(data, code=err["code"], title=err.get("message", "Unknown error"))

        # set the error and lookup the callback
        with self._lock:
            if res["id"] in self._results:
                self._results[res["id"]] = error
            callback = self._callbacks.pop(res["id"], None)

        # invoke the callback
        if callback is not None:
            callback(error, None)

    def _route(self, method: str) -> Any:
        """
        Returns the method of the wrapped target object to be called when *method* is requested. For security
        reasons, attributes starting with two underscores (e.g. dunder or name-mangled attributes) are not accessible
        and the resolved object must be callable.

        :param method: The method to route to.
        :return: The method to call.
        :raises RPCMethodNotFound: When the method is not found.

        Example:

        .. code-block:: python

            class MyClassB(object):
                def foo(self):
                    return 123

            class MyClassA(object):
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
        # recursively traverse public target attributes
        missing = object()
        obj = self.target
        for part in method.split("."):
            if not part or part.startswith("__"):
                break
            obj = getattr(obj, part, missing)
            if obj is missing:
                break
        else:
            if callable(obj):
                return obj

        raise RPCMethodNotFound(data=method)

    def _write(self, s: str) -> None:
        """
        Writes a string *s* to the output stream.

        :param s: The string to write.
        :return: None.
        """
        with self._write_lock:
            self.stdout.write(f"{s}\n".encode())
            self.stdout.flush()


class Watchdog(threading.Thread):
    """
    This class represents a thread that watches the input stream of an :py:class:`RPC` instance for incoming content and
    dispatches requests to it.

    :param rpc: The :py:class:`RPC` instance to watch.
    :param name: The thread's name.
    :param interval: The polling interval of the run loop.
    :param daemon: The thread's daemon flag.
    :param start: Whether to start the thread immediately.

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
        self,
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
        self._stop_event = threading.Event()

        if start:
            self.start()

    def start(self) -> None:
        """
        Starts the thread's activity.

        :return: None.
        """
        super().start()

    def stop(self) -> None:
        """
        Stops the thread's activity. While waiting for input, the run loop notices this within *interval* seconds,
        except on Windows where it only does so once new content or EOF is received.

        :return: None.
        """
        self._stop_event.set()

    def run(self) -> None:
        """
        The main run loop of the watchdog thread. Reads the input stream of the :py:class:`RPC` instance and dispatches
        incoming content to it.

        :return: None.
        """
        # reset the stop event
        self._stop_event.clear()

        # read new incoming lines
        buffer = b""
        while not self._stop_event.is_set():
            # stop when stdin is closed
            if self.rpc.stdin.closed or self.rpc.original_stdin.closed:
                break

            # read the next chunk from stdin
            try:
                fd = self.rpc.stdin.fileno()
                # wait for content in intervals so that stopping takes effect while idle
                if _can_select and not select.select([fd], [], [], self.interval)[0]:
                    continue
                chunk = os.read(fd, 65536)
            except (OSError, ValueError):
                # prevent residual race conditions occurring when stdin is closed externally
                self._stop_event.wait(self.interval)
                continue

            # an empty read signals EOF, i.e., the other end closed the stream
            if not chunk:
                self._handle_line(buffer)
                self.stop()
                break

            # handle all complete lines and keep the remainder
            *lines, buffer = (buffer + chunk).split(b"\n")
            for line in lines:
                self._handle_line(line)

    def _handle_line(self, line: bytes) -> None:
        """
        Decodes and passes a *line* to the :py:class:`RPC` instance unless it is empty. Exceptions are logged rather
        than raised to keep the watchdog alive.

        :param line: The line to handle.
        :return: None.
        """
        try:
            if (s_line := line.decode("utf-8").strip()):
                self.rpc._handle(s_line)
        except Exception:
            logger.exception("failed to handle incoming line")


class RPCError(Exception):
    """
    Base class for RPC errors.

    :param data: Additional error data.

    .. py:attribute:: code_range

        The range of error codes that this error class is responsible for.

    .. py:attribute:: code

        The error code of this error.

    .. py:attribute:: title

        The title of this error.

    .. py:attribute:: message

        The message of this error, i.e., ``"<title> (<code>)[, data: <data>]"``.

    .. py:attribute:: data

        Additional data of this error.

    *code* and *title* can be passed to override the class-level defaults, e.g. for errors with codes that have no
    registered error class.
    """

    code_range: tuple[int, int]
    code: int
    title: str

    @classmethod
    def is_code_range(cls, code: Any) -> bool:
        """
        Returns *True* when *code* is a valid error code range, i.e., a tuple of two integers where the first integer is
        less or equal to the second integer.

        :param code: The code to check.
        :return: Whether *code* is a valid error code range.
        """
        return (
            isinstance(code, tuple) and
            len(code) == 2 and
            all(isinstance(i, int) for i in code) and
            code[0] <= code[1]
        )

    def __init__(self, data: Any = None, *, code: int | None = None, title: str | None = None) -> None:
        if code is not None:
            self.code = code
        if title is not None:
            self.title = title

        # build the error message
        message = f"{self.title} ({self.code})"
        if data is not None:
            message += f", data: {data}"
        self.message = message

        super().__init__(message)

        self.data = data

    def __str__(self) -> str:
        return self.message


error_map_code: dict[int, type[RPCError]] = {}
error_map_code_range: dict[tuple[int, int], type[RPCError]] = {}


def register_error(cls: type[RPCError]) -> type[RPCError]:
    """
    Decorator that registers a new RPC error derived from :py:class:`RPCError`. The purpose of error registration is to
    have a mapping of error codes/code ranges to error classes for faster lookups during error creation.

    .. code-block:: python

        @register_error
        class MyCustomRPCError(RPCError):
            code_range = (lower_bound, upper_bound)  # both inclusive
            code = code_range[0]  # default code when used as is
            title = "My custom error"

    :param cls: The error class to register.
    :return: The error class.
    :raises TypeError: When *cls* is not a subclass of :py:class:`RPCError` or has an invalid code range.
    :raises ValueError: When the code is not within the code range, or the code range overlaps with that of an already
        registered error class.
    """
    if not isinstance(cls, type) or not issubclass(cls, RPCError):
        raise TypeError(f"'{cls}' is not a subclass of RPCError")

    # check the code range and code
    code_range = getattr(cls, "code_range", None)
    if not cls.is_code_range(code_range):
        raise TypeError(f"'{cls}' has an invalid code range {code_range}")
    if not isinstance(cls.code, int) or not code_range[0] <= cls.code <= code_range[1]:  # type: ignore[index]
        raise ValueError(f"code {cls.code} of '{cls}' is not within its code range {code_range}")

    # check overlaps with registered errors
    for (lower, upper), other in error_map_code_range.items():
        if lower <= code_range[1] and code_range[0] <= upper:  # type: ignore[index]
            raise ValueError(f"code range {code_range} of '{cls}' overlaps with that of '{other}'")

    # register
    error_map_code[cls.code] = cls
    error_map_code_range[cls.code_range] = cls

    return cls


def get_error(code: int) -> type[RPCError]:
    """
    Returns the RPC error class that was previously registered to *code*. A ``ValueError`` is raised if no error class
    was found for *code*.

    :param code: The error code to look up.
    :return: The error class.
    :raises ValueError: When no error class was found for *code*.
    """
    if code in error_map_code:
        return error_map_code[code]

    for (lower, upper), cls in error_map_code_range.items():
        if lower <= code <= upper:
            return cls

    raise ValueError(f"unknown error code '{code}' ({type(code)})")


@register_error
class RPCParseError(RPCError):

    code_range = (-32700, -32700)
    code = code_range[0]
    title = "Parse error"


@register_error
class RPCInvalidRequest(RPCError):

    code_range = (-32600, -32600)
    code = code_range[0]
    title = "Invalid Request"


@register_error
class RPCMethodNotFound(RPCError):

    code_range = (-32601, -32601)
    code = code_range[0]
    title = "Method not found"


@register_error
class RPCInvalidParams(RPCError):

    code_range = (-32602, -32602)
    code = code_range[0]
    title = "Invalid params"


@register_error
class RPCInternalError(RPCError):

    code_range = (-32603, -32603)
    code = code_range[0]
    title = "Internal error"


@register_error
class RPCServerError(RPCError):

    code_range = (-32099, -32000)
    code = code_range[0]  # default code when used as is
    title = "Server error"
