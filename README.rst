.. image:: https://travis-ci.org/agronholm/typeguard.svg?branch=master
  :target: https://travis-ci.org/agronholm/typeguard
  :alt: Build Status
.. image:: https://coveralls.io/repos/agronholm/typeguard/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/agronholm/typeguard?branch=master
  :alt: Code Coverage

.. highlight:: python

This library provides run-time type checking for functions defined with argument type annotations.

The ``typing`` module introduced in Python 3.5 (and available on PyPI for older versions of
Python 3) is supported. See below for details.

There are three principal ways to use type checking, each with its pros and cons:

#. calling ``check_argument_types()`` from within the function body:

   * debugger friendly
   * cannot check the type of the return value
   * does not work reliably with dynamically defined type hints (e.g. in nested functions)
#. decorating the function with ``@typechecked``:

   * can check the type of the return value
   * adds an extra frame to the call stack for every call to a decorated function
#. using ``with TypeChecker() as checker:``:

   * eliminates boilerplate
   * can be stacked/nested
   * noninvasive (only records type violations; does not raise exceptions)
   * does not work reliably with dynamically defined type hints (e.g. in nested functions)
   * may cause problems with badly behaving debuggers or profilers

If a function is called with incompatible argument types or a ``@typechecked`` decorated function
returns a value incompatible with the declared type, a descriptive ``TypeError`` exception is
raised.

Type checks can be fairly expensive so it is recommended to run Python in "optimized" mode
(``python -O`` or setting the ``PYTHONOPTIMIZE`` environment variable) when running code containing
type checks in production. The optimized mode will disable the type checks, by virtue of removing
all ``assert`` statements and setting the ``__debug__`` constant to ``False``.

Using ``check_argument_types()``::

    from typeguard import check_argument_types

    def some_function(a: int, b: float, c: str, *args: str):
        assert check_argument_types()
        ...

Using ``@typechecked``::

    from typeguard import typechecked

    @typechecked
    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        ...

To enable type checks even in optimized mode::

    @typechecked(always=True)
    def foo(a: str, b: int, c: Union[str, int]) -> bool:
        ...

Using ``with typechecking():``::

    # All calls are checked everywhere until the context block is exited
    with typechecking():
        run_my_application()

Using TypeChecker::

    from typeguard import TypeChecker

    with TypeChecker(['mypackage', 'otherpackage']) as checker:
        foo(1, 2, 'a', 'b')

    for violation in checker.violations:
        print(violation)

The following types from the ``typing`` package have specialized support:

============== ============================================================
Type           Notes
============== ============================================================
``Dict``       Keys and values are typechecked
``List``       Contents are typechecked
``Set``        Contents are typechecked
``Tuple``      Contents are typechecked
``NamedTuple`` Field values are typechecked
``Callable``   Argument count is checked but types are not (yet)
``TypeVar``    Constraints, bound types and co/contravariance are supported
               but custom generic types are not (due to type erasure)
``Union``
============== ============================================================


Project links
-------------

* `Change log <https://github.com/agronholm/typeguard/blob/master/CHANGELOG.rst>`_
* `Source repository <https://github.com/agronholm/typeguard>`_
* `Issue tracker <https://github.com/agronholm/typeguard/issues>`_
