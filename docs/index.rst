jsonrpyc
========

.. centered:: This page contains only API docs. For more info, visit `jsonrpyc on GitHub <https://github.com/riga/jsonrpyc>`_.


.. toctree::
   :maxdepth: 2


.. automodule:: jsonrpyc

``RPC``
-------

.. autoclass:: RPC
   :members:


``Spec``
--------

.. autoclass:: Spec
   :members:


``Watchdog``
------------

.. autoclass:: Watchdog
   :members:


``RPCError``
------------

.. autoexception:: RPCError
   :members:

.. autofunction:: register_error

.. autofunction:: get_error


RPC errors
----------

.. autoexception:: RPCParseError
   :members:
   :undoc-members:

.. autoexception:: RPCInvalidRequest
   :members:
   :undoc-members:

.. autoexception:: RPCMethodNotFound
   :members:
   :undoc-members:

.. autoexception:: RPCInvalidParams
   :members:
   :undoc-members:

.. autoexception:: RPCInternalError
   :members:
   :undoc-members:

.. autoexception:: RPCServerError
   :members:
   :undoc-members:
