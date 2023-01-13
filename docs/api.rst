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

.. autoclass:: ForwardRefPolicy
    :members:

.. autofunction:: warn_on_error

.. autoexception:: TypeCheckError

.. autoexception:: TypeCheckWarning

.. autoexception:: TypeHintWarning

:mod:`typeguard.importhook`
---------------------------

.. module:: typeguard.importhook

.. autoclass:: TypeguardFinder
    :members:

.. autofunction:: install_import_hook
