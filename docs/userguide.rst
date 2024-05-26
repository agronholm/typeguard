User guide
==========

.. py:currentmodule:: typeguard

Checking types directly
-----------------------

The most straightfoward way to do type checking with Typeguard is with
:func:`.check_type`. It can be used as as a beefed-up version of :func:`isinstance` that
also supports checking against annotations in the :mod:`typing` module::

    from typeguard import check_type

    # Raises TypeCheckError if there's a problem
    check_type([1234], List[int])

It's also useful for safely casting the types of objects dynamically constructed from
external sources::

    import json
    from typing import List, TypedDict

    from typeguard import check_type

    # Example contents of "people.json":
    # [
    #   {"name": "John Smith", "phone": "111-123123", "address": "123 Main Street"},
    #   {"name": "Jane Smith", "phone": "111-456456", "address": "123 Main Street"}
    # ]

    class Person(TypedDict):
        name: str
        phone: str
        address: str

     with open("people.json") as f:
        people = check_type(json.load(f), List[Person])

With this code, static type checkers will recognize the type of ``people`` to be
``List[Person]``.

Using the decorator
-------------------

The :func:`@typechecked <typechecked>` decorator is the simplest way to add type
checking on a case-by-case basis. It can be used on functions directly, or on entire
classes, in which case all the contained methods are instrumented::

    from typeguard import typechecked

    @typechecked
    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        ...
        return retval

    @typechecked
    class SomeClass:
        # All type annotated methods (including static and class methods and properties)
        # are type checked.
        # Does not apply to inner classes!
        def method(x: int) -> int:
            ...

The decorator instruments functions by fetching the source code, parsing it to an
abstract syntax tree using :func:`ast.parse`, modifying it to add type checking, and
finally compiling the modified AST into byte code. This code is then used to make a new
function object that is used to replace the original one.

To explicitly set type checking options on a per-function basis, you can pass them as
keyword arguments to :func:`@typechecked <typechecked>`::

    from typeguard import CollectionCheckStrategy, typechecked

    @typechecked(collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS)
    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        ...
        return retval

This also allows you to override the global options for specific functions when using
the import hook.

.. note:: You should always place this decorator closest to the original function,
    as it will not work when there is another decorator wrapping the function.
    For the same reason, when you use it on a class that has wrapping decorators on
    its methods, such methods will not be instrumented. In contrast, the import hook
    has no such restrictions.

Using the import hook
---------------------

The import hook, when active, automatically instruments all type annotated functions to
type check arguments, return values and values yielded by or sent to generator
functions. This allows for a non-invasive method of run time type checking. This method
does not modify the source code on disk, but instead modifies its AST (Abstract Syntax
Tree) when the module is loaded.

Using the import hook is as straightforward as installing it before you import any
modules you wish to be type checked. Give it the name of your top level package (or a
list of package names)::

    from typeguard import install_import_hook

    install_import_hook('myapp')
    from myapp import some_module  # import only AFTER installing the hook, or it won't take effect

If you wish, you can uninstall the import hook::

    manager = install_import_hook('myapp')
    from myapp import some_module
    manager.uninstall()

or using the context manager approach::

    with install_import_hook('myapp'):
        from myapp import some_module

You can also customize the logic used to select which modules to instrument::

    from typeguard import TypeguardFinder, install_import_hook

    class CustomFinder(TypeguardFinder):
        def should_instrument(self, module_name: str):
            # disregard the module names list and instrument all loaded modules
            return True

    install_import_hook('', cls=CustomFinder)

.. _forwardrefs:

Notes on forward reference handling
-----------------------------------

The internal type checking functions, injected to instrumented code by either
:func:`@typechecked <typechecked>` or the import hook, use the "naked" versions of any
annotations, undoing any quotations in them (and the effects of
``from __future__ import annotations``). As such, in instrumented code, the
:attr:`~.TypeCheckConfiguration.forward_ref_policy` only applies when using type
variables containing forward references, or type aliases likewise containing forward
references.

To facilitate the use of types only available to static type checkers, Typeguard
recognizes module-level imports guarded by ``if typing.TYPE_CHECKING:`` or
``if TYPE_CHECKING:`` (add the appropriate :mod:`typing` imports). Imports made within
such blocks on the module level will be replaced in calls to internal type checking
functions with :data:`~typing.Any`.

Using the pytest plugin
-----------------------

Typeguard comes with a plugin for pytest (v7.0 or newer) that installs the import hook
(explained in the previous section). To use it, run ``pytest`` with the appropriate
``--typeguard-packages`` option. For example, if you wanted to instrument the
``foo.bar`` and ``xyz`` packages for type checking, you can do the following:

.. code-block:: bash

    pytest --typeguard-packages=foo.bar,xyz

It is also possible to set option for the pytest plugin using pytest's own
configuration. For example, here's how you might specify several options in
``pyproject.toml``:

.. code-block:: toml

    [tool.pytest.ini_options]
    typeguard-packages = """
    foo.bar
    xyz"""
    typeguard-debug-instrumentation = true
    typeguard-typecheck-fail-callback = "mypackage:failcallback"
    typeguard-forward-ref-policy = "ERROR"
    typeguard-collection-check-strategy = "ALL_ITEMS"

See the next section for details on how the individual options work.

.. note:: There is currently no support for specifying a customized module finder.

Setting configuration options
-----------------------------

There are several configuration options that can be set that influence how type checking
is done. The :data:`typeguard.config` (which is of type
:class:`~.TypeCheckConfiguration`) controls the options applied to code instrumented via
either :func:`@typechecked <.typechecked>` or the import hook. The
:func:`~.check_type`, function, however, uses the built-in defaults and is not affected
by the global configuration, so you must pass any configuration overrides explicitly
with each call.

You can also override specific configuration options in instrumented functions (or
entire classes) by passing keyword arguments to :func:`@typechecked <.typechecked>`.
You can do this even if you're using the import hook, as the import hook will remove the
decorator to ensure that no double instrumentation takes place. If you're using the
import hook to type check your code only during tests and don't want to include
``typeguard`` as a run-time dependency, you can use a dummy replacement for the
decorator.

For example, the following snippet will only import the decorator during a pytest_ run::

    import sys

    if "pytest" in sys.modules:
        from typeguard import typechecked
    else:
        from typing import TypeVar
        _T = TypeVar("_T")

        def typechecked(target: _T, **kwargs) -> _T:
            return target if target else typechecked

.. _pytest: https://docs.pytest.org/

Suppressing type checks
-----------------------

Temporarily disabling type checks
+++++++++++++++++++++++++++++++++

If you need to temporarily suppress type checking, you can use the
:func:`~.suppress_type_checks` function, either as a context manager or a decorator, to
skip the checks::

    from typeguard import check_type, suppress_type_checks

    with suppress_type_checks():
        check_type(1, str)  # would fail without the suppression

    @suppress_type_checks
    def my_suppressed_function(x: int) -> None:
        ...

Suppression state is tracked globally. Suppression ends only when all the context
managers have exited and all calls to decorated functions have returned.

Permanently suppressing type checks for selected functions
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

To exclude specific functions from run time type checking, you can use one of the
following decorators:

  * :func:`@typeguard_ignore <typeguard_ignore>`: prevents the decorated
    function from being instrumentated by the import hook
  * :func:`@no_type_check <typing.no_type_check>`: as above, but disables static type
    checking too

For example, calling the function defined below will not result in a type check error
when the containing module is instrumented by the import hook::

    from typeguard import typeguard_ignore

    @typeguard_ignore
    def f(x: int) -> int:
        return str(x)

.. warning:: The :func:`@no_type_check_decorator <typing.no_type_check_decorator>`
    decorator is not currently recognized by Typeguard.

Suppressing the ``@typechecked`` decorator in production
--------------------------------------------------------

If you're using the :func:`@typechecked <typechecked>` decorator to gradually introduce
run-time type checks to your code base, you can disable the checks in production by
running Python in optimized mode (as opposed to debug mode which is the default mode).
You can do this by either starting Python with the ``-O`` or ``-OO`` option, or by
setting the PYTHONOPTIMIZE_ environment variable. This will cause
:func:`@typechecked <typechecked>` to become a no-op when the import hook is not being
used to instrument the code.

.. _PYTHONOPTIMIZE: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONOPTIMIZE

Debugging instrumented code
---------------------------

If you find that your code behaves in an unexpected fashion with the Typeguard
instrumentation in place, you should set the ``typeguard.config.debug_instrumentation``
flag to ``True``. This will print all the instrumented code after the modifications,
which you can check to find the reason for the unexpected behavior.

If you're using the pytest plugin, you can also pass the
``--typeguard-debug-instrumentation`` and ``-s`` flags together for the same effect.
