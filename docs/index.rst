Typeguard
=========

.. toctree::
   :maxdepth: 2
   :caption: Quick links:

   api
   versionhistory

Using type checker functions
----------------------------

Two functions are provided, potentially for use with the ``assert`` statement:

* :func:`~typeguard.check_argument_types`
* :func:`~typeguard.check_return_type`

These can be used to implement fine grained type checking for select functions.
If the function is called with incompatible types, or :func:`~typeguard.check_return_type` is used
and the return value does not match the return type annotation, then a :exc:`TypeError` is raised.

For example::

    from typeguard import check_argument_types, check_return_value

    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        assert check_argument_types()
        ...
        assert check_return_value(retval)
        return retval

When combined with the ``assert`` statement, these checks are automatically removed from the code
by the compiler when Python is executed in optimized mode (by passing the ``-O`` switch to the
interpreter, or by setting the ``PYTHONOPTIMIZE`` environment variable to ``1`` (or higher).

.. note:: This method is not reliable when used in nested functions (i.e. functions defined inside
   other functions). This is because this operating mode relies on finding the correct function
   object using the garbage collector, and when a nested function is running, its function object
   may no longer be around anymore, as it is only bound to the closure of the enclosing function.
   For this reason, it is recommended to use ``@typechecked`` instead for nested functions.

Using the decorator
-------------------

The simplest way to type checking of both argument values and the return value for a single
function is to use the ``@typechecked`` decorator::

    from typeguard import typechecked

    @typechecked
    def some_function(a: int, b: float, c: str, *args: str) -> bool:
        ...
        return retval

    @typechecked
    class SomeClass:
        # All type annotated methods (including static and class methods) are type checked.
        # Does not apply to inner classes!
        def method(x: int) -> int:
            ...

The decorator works just like the two previously mentioned checker functions except that it has no
issues with nested functions. The drawback, however, is that it adds one stack frame per wrapped
function which may make debugging harder.

When a generator function is wrapped with ``@typechecked``, the yields, sends and the return value
are also type checked against the :class:`~typing.Generator` annotation. The same applies to the
yields and sends of an async generator (annotated with :class:`~typing.AsyncGenerator`).

.. note::
   The decorator also respects the optimized mode setting so it does nothing when the interpreter
   is running in optimized mode.

Using the profiler hook
-----------------------

This type checking approach requires no code changes, but does come with a number of drawbacks.
It relies on setting a profiler hook in the interpreter which gets called every time a new Python
stack frame is entered or exited.

The easiest way to use this approach is to use a :class:`~typeguard.TypeChecker` as a context
manager::

    from warnings import filterwarnings

    from typeguard import TypeChecker, TypeWarning

    # Display all TypeWarnings, not just the first one
    filterwarnings('always', category=TypeWarning)

    # Run your entire application inside this context block
    with TypeChecker(['mypackage', 'otherpackage']):
        mypackage.run_app()

Alternatively, manually start (and stop) the checker::

    checker = TypeChecker(['mypackage', 'otherpackage'])
    checker.start()
    mypackage.start_app()

The profiler hook approach has the following drawbacks:

* Return values of ``None`` are not type checked, as they cannot be distinguished from exceptions
  being raised
* The hook relies on finding the target function using the garbage collector which may make it
  miss some type violations, especially with nested functions
* Generator yield types are checked, send types are not
* Generator yields cannot be distinguished from returns
* Async generators are not type checked at all

.. hint:: Some other things you can do with :class:`~typeguard.TypeChecker`:

 * Display all warnings from the start with ``python -W always::typeguard.TypeWarning``
 * Redirect them to logging using :func:`logging.captureWarnings`
 * Record warnings in your pytest test suite and fail test(s) if you get any
   (see the `pytest documentation`_ about that)

.. _pytest documentation: http://doc.pytest.org/en/latest/warnings.html#assertwarnings

Checking types directly
-----------------------

Typeguard can also be used as a beefed-up version of :func:`isinstance` that also supports checking
against annotations in the :mod:`typing` module::

    from typeguard import check_type

    # Raises TypeError if there's a problem
    check_type('variablename', [1234], List[int])

Supported typing.* types
------------------------

The following types from the ``typing`` package have specialized support:

============== ============================================================
Type           Notes
============== ============================================================
``Callable``   Argument count is checked but types are not (yet)
``Dict``       Keys and values are typechecked
``List``       Contents are typechecked
``Literal``
``NamedTuple`` Field values are typechecked
``Set``        Contents are typechecked
``Sequence``   Contents are typechecked
``Tuple``      Contents are typechecked
``Type``
``TypeVar``    Constraints, bound types and co/contravariance are supported
               but custom generic types are not (due to type erasure)
``Union``
============== ============================================================
