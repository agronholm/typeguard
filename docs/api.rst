API reference
=============

:mod:`typeguard`
----------------

.. module:: typeguard

.. autofunction:: check_type

.. autofunction:: check_argument_types

.. autofunction:: check_return_type

.. autodecorator:: typechecked

.. autodecorator:: typeguard_ignore

.. autofunction:: suppress_type_checks

.. autoclass:: TypeCheckConfiguration
   :members:

.. data:: config
   :type: TypeCheckConfiguration

   The global configuration object.

.. autoclass:: ForwardRefPolicy
    :members:

.. autofunction:: warn_on_error

.. autofunction:: check_type_internal

.. autoclass:: TypeCheckMemo
    :members:

.. autoclass:: CallMemo
    :members:

.. data:: checker_lookup_functions
   :type: list[Callable[[Any, Tuple[Any, ...], Tuple[Any, ...]], Optional[Callable[[Any, Any, Tuple[Any, ...], TypeCheckMemo], Any]]]]

   A list of callables that are used to look up a checker callable for an annotation.

.. autoexception:: TypeCheckError

.. autoexception:: TypeCheckWarning

.. autoexception:: TypeHintWarning

:mod:`typeguard.importhook`
---------------------------

.. module:: typeguard.importhook

.. autoclass:: TypeguardFinder
    :members:

.. autoclass:: ImportHookManager
    :members:

.. autofunction:: install_import_hook
