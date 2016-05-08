.. image:: https://travis-ci.org/agronholm/typeguard.svg?branch=master
  :target: https://travis-ci.org/agronholm/typeguard
  :alt: Build Status
.. image:: https://coveralls.io/repos/agronholm/typeguard/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/agronholm/typeguard?branch=master
  :alt: Code Coverage

This library provides run-time type checking for functions defined with argument type annotations.

The ``typing`` module introduced in Python 3.5 (and available on PyPI for older versions of
Python 3) is supported. See below for details.

There are two principal ways to use type checking, each with its pros and cons:

#. calling ``check_argument_types()`` from within the function body:
    debugger friendly but cannot check the type of the return value
#. decorating the function with ``@typechecked``:
    can check the type of the return value but adds an extra frame to the call stack for every call
    to a decorated function

If a function is called with incompatible argument types or a ``@typechecked`` decorated function
returns a value incompatible with the declared type, a descriptive ``TypeError`` exception is
raised.

Type checks can be fairly expensive so it is recommended to run Python in "optimized" mode
(``python -O`` or setting the ``PYTHONOPTIMIZE`` environment variable) when running code containing
type checks in production. The optimized mode will disable the type checks, by virtue of removing
all ``assert`` statements and setting the ``__debug__`` constant to ``False``.

Using ``check_argument_types()``:

.. code-block:: python

    from typeguard import check_argument_types

    def some_function(a: int, b: float, c: str, *args: str):
        assert check_argument_types()
        ...

Using ``@typechecked``:

.. code-block:: python

    from typeguard import typechecked

    @typechecked
    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        ...

To enable type checks even in optimized mode:

.. code-block:: python

    @typechecked(always=True)
    def foo(a: str, b: int, c: Union[str, int]) -> bool:
       ...


The following types from the ``typing`` package have specialized support:

============ ============================================================
Type         Notes
============ ============================================================
``Dict``     Keys and values are typechecked
``List``     Contents are typechecked
``Set``      Contents are typechecked
``Tuple``    Contents are typechecked
``Callable`` Argument count is checked but types are not (yet)
``TypeVar``  Constraints, bound types and co/contravariance are supported
             but custom generic types are not (due to type erasure)
``Union``
============ ============================================================


Project links
-------------

* `Change log <https://github.com/agronholm/typeguard/blob/master/CHANGELOG.rst>`_
* `Source repository <https://github.com/agronholm/typeguard>`_
* `Issue tracker <https://github.com/agronholm/typeguard/issues>`_
