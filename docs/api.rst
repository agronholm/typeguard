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

.. data:: checker_lookup_functions
   :type: list[TypeCheckLookupCallback]
   :canonical: typeguard._checkers.checker_lookup_functions

   A list of callables that are used to look up a checker callable for an annotation.

.. autoexception:: TypeCheckError

.. autoexception:: TypeCheckWarning

.. autoexception:: TypeHintWarning

:mod:`typeguard.importhook`
---------------------------

.. module:: typeguard.importhook

.. autoclass:: TypeguardFinder
    :members:

.. autofunction:: install_import_hook
