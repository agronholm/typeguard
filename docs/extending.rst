Extending Typeguard
===================

.. py:currentmodule:: typeguard

Adding new type checkers
------------------------

The range of types supported by Typeguard can be extended by writing a plugin.
When Typeguard's configuration is being set up, it will load all `entry points`_ in the
``typeguard.checker_lookup`` group. Each one is a callable that may return a callback that gets
called when a matching annotation is encountered::

    from inspect import isclass
    from typing import Any, Optional, Tuple

    from typeguard import TypeCheckError, TypeCheckerCallable, TypeCheckMemo


    class MySpecialType:
        pass


    def check_my_special_type(
        value: Any, origin_type: Any, args: Tuple[Any, ...], memo: TypeCheckMemo
    ) -> None:
        if not isinstance(value, MySpecialType):
            raise TypeCheckError('is not my special type')


    def my_checker_lookup(
        origin_type: Any, args: Tuple[Any, ...], extras: Tuple[Any, ...]
    ) -> Optional[TypeCheckerCallable]:
        if isclass(origin_type) and issubclass(origin_type, MySpecialType):
            return check_my_special_type

        return None

The lookup function receives three arguments:

#. The origin type (the annotation with any arguments stripped from it)
#. The previously stripped out generic arguments, if any
#. Extra arguments from the ``Annotated`` annotation, if any

For example, if the annotation was ``Tuple``,, the lookup function would be called with
``Tuple, (), ()``. If the type was parametrized, like ``Tuple[str, int]``, it would be
called with ``Tuple, (str, int), ()``. If the annotation was
``Annotated[Tuple[str, int], 'foo', 'bar']``, the arguments would instead be
``Tuple, (str, int), ('foo', 'bar')``.

In order to let Typeguard find the entry point, it has to be present in the distribution metadata.
You should consult the documentation of whatever Python packaging framework you are using, but for
Setuptools, you can add this to your ``setup.cfg``:

.. code-block:: ini

    [options.entry_points]
    typeguard.checker_lookup =
        myplugin = myapp.my_plugin_module:my_checker_lookup

.. note:: After modifying your project configuration, you may have to reinstall it in order for
          the entry point to become discoverable.

.. _entry points: https://docs.python.org/3/library/importlib.metadata.html#entry-points
