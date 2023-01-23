User guide
==========

.. py:currentmodule:: typeguard

Setting configuration options
-----------------------------

There are several configuration options that can be set that influence how type checking
is done. To change the options, import ``typeguard.config`` (which is of type
:class:`~.TypeCheckConfiguration`) and set the attributes you want to change.

You can also override the configuration in the type checking functions below by passing
them a custom configuration object.

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

Using type checker functions
----------------------------

Two functions are provided, potentially for use with the ``assert`` statement:

* :func:`~typeguard.check_argument_types`
* :func:`~typeguard.check_return_type`
* :func:`~typeguard.check_yield_type`

These can be used to implement fine grained type checking for select functions.
If the function is called with incompatible types, or :func:`~typeguard.check_return_type` is used
and the return value does not match the return type annotation, then a :exc:`~.TypeCheckError` is raised.

For example::

    from typeguard import check_argument_types, check_return_type

    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        assert check_argument_types()
        ...
        assert check_return_type(retval)
        return retval

When combined with the ``assert`` statement, these checks are automatically removed from the code
by the compiler when Python is executed in optimized mode (by passing the ``-O`` switch to the
interpreter, or by setting the ``PYTHONOPTIMIZE`` environment variable to ``1`` (or higher).

.. note:: This method is not reliable when used in nested functions (i.e. functions defined inside
   other functions). This is because this operating mode relies on finding the correct function
   object using the garbage collector, and when a nested function is running, its function object
   may no longer be around anymore, as it is only bound to the closure of the enclosing function.
   For this reason, it is recommended to use :func:`@typechecked <typechecked>` instead
   for nested functions.

Using the decorator
-------------------

The simplest way to type checking of both argument values and the return value for a single
function is to use the :func:`@typechecked <typechecked>` decorator::

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

The decorator works just like the two previously mentioned checker functions except that it has no
issues with nested functions. The drawback, however, is that it adds one stack frame per wrapped
function which may make debugging harder.

When a generator function is wrapped with :func:`@typechecked <typechecked>`, the
yields, sends and the return value are also type checked against the
:class:`~typing.Generator` annotation. The same applies to the yields and sends of an
async generator (annotated with :class:`~typing.AsyncGenerator`).

.. note::
   The decorator also respects the optimized mode setting so it does nothing when the interpreter
   is running in optimized mode.

Using the import hook
---------------------

The import hook, when active, automatically instruments all type annotated functions to
type check arguments, return values and yield values (for generators). This allows for a
noninvasive method of run time type checking. This method does not modify the source
code on disk, but instead modifies its AST (Abstract Syntax Tree) when the module is
loaded.

Using the import hook is as straightforward as installing it before you import any
modules you wish to be type checked. Give it the name of your top level package (or a
list of package names)::

    from typeguard.importhook import install_import_hook

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

    from typeguard.importhook import TypeguardFinder, install_import_hook

    class CustomFinder(TypeguardFinder):
        def should_instrument(self, module_name: str):
            # disregard the module names list and instrument all loaded modules
            return True

    install_import_hook('', cls=CustomFinder)

To exclude specific functions or classes from run time type checking, use the
:func:`@typeguard_ignore <typeguard_ignore>` decorator::

    from typeguard import typeguard_ignore

    @typeguard_ignore
    def f(x: int) -> int:
        return str(x)

Unlike :func:`~typing.no_type_check`, this decorator has no effect on static type
checking.

Using PEP 604 unions on Pythons older than 3.10
-----------------------------------------------

The :pep:`604` ``X | Y`` notation was introduced in Python 3.10, but it can be used with
older Python versions in modules where ``from __future__ import annotations`` is
present. Typeguard contains a special parser that lets it convert these to older
:class:`~typing.Union` annotations internally.

Using the pytest plugin
-----------------------

Typeguard comes with a pytest plugin that installs the import hook (explained in the previous
section). To use it, run ``pytest`` with the appropriate ``--typeguard-packages`` option. For
example, if you wanted to instrument the ``foo.bar`` and ``xyz`` packages for type checking, you
can do the following:

.. code-block:: bash

    pytest --typeguard-packages=foo.bar,xyz

There is currently no support for specifying a customized module finder.

Temporarily disabling type checks
---------------------------------

If you need to temporarily suppress type checking, you can use the
:func:`~.suppress_type_checks` context manager to skip the checks::

    from typeguard import check_type, suppress_type_checks

    with suppress_type_checks():
        check_type(1, str)  # would fail without the suppression

These context managers will stack, so type checking is only done once all such context
managers have exited.

Support for mock objects
------------------------

Typeguard handles the :class:`unittest.mock.Mock` class (and its subclasses) specially,
bypassing any type checks when encountering instances of these classes. Note that any
"spec" class passed to the mock object is currently not respected.

Supported typing.* types
------------------------

The following types from the ``typing`` (and ``typing_extensions``) package have specialized
support:

================== =============================================================
Type               Notes
================== =============================================================
``Any``            Any value passes when checked against ``Any``. An instance of a class
                   inheriting from ``Any`` (``typing.Any`` on Python 3.11+, or
                   ``typing_extensions.Any``) will pass any type check.
``Annotated``      Original annotation is unwrapped and typechecked normally
``AbstractSet``    Contents are typechecked
``BinaryIO``       Specialized instance checks are performed
``Callable``       Argument count is checked but types are not (yet)
``Dict``           Keys and values are typechecked
``IO``             Specialized instance checks are performed
``List``           Contents are typechecked
``Literal``
``LiteralString``  Checked as :class:`str`
``Mapping``        Keys and values are typechecked
``MutableMapping`` Keys and values are typechecked
``NamedTuple``     Field values are typechecked
``Never``          Supported in argument and return type annotations
``NoReturn``       Supported in argument and return type annotations
``Protocol``       Run-time protocols are checked with :func:`isinstance`,
                   others are ignored
``Self``           Assumes first call argument to be a valid ``Self``; won't know if
                   the called function is actually a method or not
``Set``            Contents are typechecked
``Sequence``       Contents are typechecked
``TextIO``         Specialized instance checks are performed
``Tuple``          Contents are typechecked
``Type``
``TypeGuard``      Checked as :class`bool`
``TypedDict``      Contents are typechecked; On Python 3.8 and earlier,
                   ``total`` from superclasses is not respected (see `#101`_ for
                   more information); On Python 3.9.0, false positives can happen when
                   constructing ``TypedDict`` classes using old-style syntax (see
                   `issue 42059`_)
``TypeVar``        Constraints and bound types are typechecked
``Union``          :pep:`604` unions are supported on Python 3.10+
================== =============================================================

.. _#101: https://github.com/agronholm/typeguard/issues/101
.. _issue 42059: https://bugs.python.org/issue42059
