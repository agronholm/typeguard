.. image:: https://travis-ci.com/agronholm/typeguard.svg?branch=master
  :target: https://travis-ci.com/agronholm/typeguard
  :alt: Build Status
.. image:: https://coveralls.io/repos/agronholm/typeguard/badge.svg?branch=master&service=github
  :target: https://coveralls.io/github/agronholm/typeguard?branch=master
  :alt: Code Coverage

This library provides run-time type checking for functions defined with argument type annotations.

The ``typing`` module introduced in Python 3.5 (and available on PyPI for older versions of
Python 3) is supported. See below for details.

There are three principal ways to use type checking, each with its pros and cons:

#. calling ``check_argument_types()`` from within the function body:

   * debugger friendly (except when running with the pydev debugger with the C extension installed)
   * cannot check the type of the return value
   * does not work reliably with dynamically defined type hints (e.g. in nested functions)
#. decorating the function with ``@typechecked``:

   * 100% reliable at finding the function object to be checked (does not need to check the garbage
     collector)
   * can check the type of the return value
   * wraps returned generators (async or regular) and type checks yields, sends and returns
   * adds an extra frame to the call stack for every call to a decorated function
#. using ``with TypeChecker('packagename'):``:

   * emits warnings instead of raising ``TypeError``
   * eliminates boilerplate
   * multiple TypeCheckers can be stacked/nested
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

Using ``check_argument_types()``:

.. code-block:: python3

    from typeguard import check_argument_types

    def some_function(a: int, b: float, c: str, *args: str):
        assert check_argument_types()
        ...

Using ``@typechecked``:

.. code-block:: python3

    from typeguard import typechecked

    @typechecked
    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        ...

    @typechecked
    class SomeClass:
        # All type annotated methods (static, class methods included) are type checked
        # Does not apply to inner classes!
        def method(x: int) -> int:
            ...

To enable type checks even in optimized mode:

.. code-block:: python3

    @typechecked(always=True)
    def foo(a: str, b: int, c: Union[str, int]) -> bool:
        ...

Using ``TypeChecker``:

.. code-block:: python3

    from warnings import filterwarnings

    from typeguard import TypeChecker, TypeWarning

    # Display all TypeWarnings, not just the first one
    filterwarnings('always', category=TypeWarning)

    # Run your entire application inside this context block
    with TypeChecker(['mypackage', 'otherpackage']):
        mypackage.run_app()

    # Alternatively, manually start (and stop) the checker:
    checker = TypeChecker('mypackage')
    checker.start()
    mypackage.start_app()

Some shortcomings in ``TypeChecker``:

* If a function returns ``None``, no return (or yield) value type checking is done because ``None``
  is also returned to the profiler hook when an exception is raised
* Generator yield types are checked, send types are not
* Generator yields cannot be distinguished from returns
* Async generators are ignored

.. hint:: Some other things you can do with ``TypeChecker``:

   * display all warnings from the start with ``python -W always::typeguard.TypeWarning``
   * redirect them to logging using ``logging.captureWarnings()``
   * record warnings in your pytest test suite and fail test(s) if you get any
     (see the `pytest documentation <http://doc.pytest.org/en/latest/recwarn.html>`_ about that)

To directly check a value against the specified type:

.. code-block:: python3

    from typeguard import check_type

    check_type('variablename', [1234], List[int])


The following types from the ``typing`` package have specialized support:

============== ============================================================
Type           Notes
============== ============================================================
``Callable``   Argument count is checked but types are not (yet)
``Dict``       Keys and values are typechecked
``List``       Contents are typechecked
``NamedTuple`` Field values are typechecked
``Set``        Contents are typechecked
``Tuple``      Contents are typechecked
``Type``
``TypeVar``    Constraints, bound types and co/contravariance are supported
               but custom generic types are not (due to type erasure)
``Union``
============== ============================================================


Project links
-------------

* `Change log <https://github.com/agronholm/typeguard/blob/master/CHANGELOG.rst>`_
* `Source repository <https://github.com/agronholm/typeguard>`_
* `Issue tracker <https://github.com/agronholm/typeguard/issues>`_
