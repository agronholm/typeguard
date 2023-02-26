Extending Typeguard
===================

.. py:currentmodule:: typeguard

Adding new type checkers
------------------------

The range of types supported by Typeguard can be extended by writing a
**type checker lookup funvtion** and one or more **type checker functions**. The former
will return one of the latter, or ``None`` if the given value does not match any of your
custom type checker functions.

The lookup function receives three arguments:

#. The origin type (the annotation with any arguments stripped from it)
#. The previously stripped out generic arguments, if any
#. Extra arguments from the :class:`~typing.Annotated` annotation, if any

For example, if the annotation was ``tuple``,, the lookup function would be called with
``tuple, (), ()``. If the type was parametrized, like ``tuple[str, int]``, it would be
called with ``tuple, (str, int), ()``. If the annotation was
``Annotated[tuple[str, int], "foo", "bar"]``, the arguments would instead be
``tuple, (str, int), ("foo", "bar")``.

The checker function receives four arguments:

#. The value to be type checked
#. The origin type
#. The generic arguments from the annotation (empty tuple when the annotation was not
   parametrized)
#. The memo object, either :class:`~.TypeCheckMemo` or :class:`~.CallMemo`

There are a couple of things to take into account when writing a type checker:

#. If your type checker function needs to do further type checks (such as type checking
   items in a collection), you need to use :func:`~.check_type_internal` (and pass
   along ``memo`` to it)
#. If you're type checking collections, your checker function should respect the
   :attr:`~.TypeCheckConfiguration.collection_check_strategy` setting, available from
   :data:`typeguard.config`

The following example contains a lookup function and type checker for a custom class
(``MySpecialType``)::

    from __future__ import annotations
    from inspect import isclass
    from typing import Any

    from typeguard import TypeCheckError, TypeCheckerCallable, TypeCheckMemo


    class MySpecialType:
        pass


    def check_my_special_type(
        value: Any, origin_type: Any, args: tuple[Any, ...], memo: TypeCheckMemo
    ) -> None:
        if not isinstance(value, MySpecialType):
            raise TypeCheckError('is not my special type')


    def my_checker_lookup(
        origin_type: Any, args: tuple[Any, ...], extras: tuple[Any, ...]
    ) -> TypeCheckerCallable | None:
        if isclass(origin_type) and issubclass(origin_type, MySpecialType):
            return check_my_special_type

        return None

Registering your type checker lookup function with Typeguard
------------------------------------------------------------

Just writing a type checker lookup function doesn't do anything by itself. You'll have
to advertise your type checker lookup function to Typeguard somehow. There are two ways
to do that (pick just one):

#. Append to :data:`typeguard.checker_lookup_functions`
#. Add an `entry point`_ to your project in the ``typeguard.checker_lookup`` group

If you're packaging your project with standard packaging tools, it may be better to add
an entry point instead of registering it manually, because manual registration requires
the registration code to run first before the lookup function can work.

To manually register the type checker lookup function with Typeguard::

    from typeguard import checker_lookup_functions

    checker_lookup_functions.append(my_checker_lookup)

For adding entry points to your project packaging metadata, the exact method may vary
depending on your packaging tool of choice, but the standard way (supported at least by
recent versions of ``setuptools``) is to add this to ``pyproject.toml``:

.. code-block:: toml

    [project.entry-points]
    typeguard.checker_lookup = {myplugin = "myapp.my_plugin_module:my_checker_lookup"}

The configuration above assumes that the **globally unique** (within the
``typeguard.checker_lookup`` namespace) entry point name for your lookup function is
``myplugin``, it lives in the ``myapp.my_plugin_module`` and the name of the function
there is ``my_checker_lookup``.

.. note:: After modifying your project configuration, you may have to reinstall it in
    order for the entry point to become discoverable.

.. _entry point: https://docs.python.org/3/library/importlib.metadata.html#entry-points
