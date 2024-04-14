**jsonrpyc**
============

.. include:: ../README.md
   :parser: myst_parser.sphinx_
   :start-after: <!-- marker-before-badges -->
   :end-before: <!-- marker-after-usage -->

API Docs
--------

.. automodule:: jsonrpyc

Classes
^^^^^^^

.. autoclass:: RPC
   :members:

.. autoclass:: Spec
   :members:

.. autoclass:: Watchdog
   :members:

.. autoexception:: RPCError
   :members:

.. autofunction:: register_error

.. autofunction:: get_error


RPC errors
^^^^^^^^^^

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


Project Info
------------

.. include:: ../README.md
   :parser: myst_parser.sphinx_
   :start-after: <!-- marker-before-info -->
   :end-before: <!-- marker-after-body -->
