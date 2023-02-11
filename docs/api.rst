API reference
=============

.. module:: typeguard

Type checking
-------------

.. autofunction:: check_type

.. autodecorator:: typechecked

Import hook
-----------

.. autofunction:: install_import_hook

.. autoclass:: TypeguardFinder
    :members:

.. autoclass:: ImportHookManager
    :members:

Configuration
-------------

.. data:: config
   :type: TypeCheckConfiguration

   The global configuration object.

.. autoclass:: TypeCheckConfiguration
   :members:

.. autoclass:: CollectionCheckStrategy

.. autoclass:: ForwardRefPolicy

.. autofunction:: warn_on_error

Custom checkers
---------------

.. autofunction:: check_type_internal

.. autofunction:: load_plugins

.. data:: checker_lookup_functions
   :type: list[Callable[[Any, Tuple[Any, ...], Tuple[Any, ...]], Optional[Callable[[Any, Any, Tuple[Any, ...], TypeCheckMemo], Any]]]]

   A list of callables that are used to look up a checker callable for an annotation.

.. autoclass:: TypeCheckMemo
    :members:

.. autoclass:: CallMemo
    :show-inheritance:
    :members:

Type check suppression
----------------------

.. autodecorator:: typeguard_ignore

.. autofunction:: suppress_type_checks

Exceptions and warnings
-----------------------

.. autoexception:: TypeCheckError

.. autoexception:: TypeCheckWarning

.. autoexception:: TypeHintWarning
