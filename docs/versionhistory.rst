Version history
===============

This library adheres to `Semantic Versioning 2.0 <https://semver.org/#semantic-versioning-200>`_.

**UNRELEASED**

- **BACKWARD INCOMPATIBLE** Made ``check_type()`` independent of ``typeguard.config``, it
  now has the same default configuration values as ``TypeCheckConfiguration`` and is
  given the ability to accept configuration options as keyword arguments.
- **BACKWARD INCOMPATIBLE** Removed ``CallMemo`` from the API
- Changed instrumentation to statically copy the function annotations to avoid having to
  look up the function object at run time
- Added support for type checking against nonlocal classes defined within the same
  parent function as the instrumented function
- Fixed ``warn_on_error()`` not showing where the type violation actually occurred
- Fixed local assignment to ``*args`` or ``**kwargs`` being type checked incorrectly
- Fixed ``TypeError`` on ``check_type(..., None)``

**3.0.1** (2023-03-16)

- Improved the documentation
- Fixed assignment unpacking (``a, b = ...``) being checked incorrectly
- Fixed ``@typechecked`` attempting to instrument wrapper decorators such as
  ``@contextmanager`` when applied to a class
- Fixed ``py.typed`` missing from the wheel when not building from a git checkout

**3.0.0** (2023-03-15)

- **BACKWARD INCOMPATIBLE** Dropped the ``argname``, ``memo``, ``globals`` and
  ``locals`` arguments from ``check_type()``
- **BACKWARD INCOMPATIBLE** Removed the ``check_argument_types()`` and
  ``check_return_type()`` functions (use ``@typechecked`` instead)
- **BACKWARD INCOMPATIBLE** Moved ``install_import_hook`` to be directly importable
  from the ``typeguard`` module
- **BACKWARD INCOMPATIBLE** Changed the checking of collections (list, set, dict,
  sequence, mapping) to only check the first item by default. To get the old behavior,
  set ``typeguard.config.collection_check_strategy`` to
  ``CollectionCheckStrategy.ALL_ITEMS``
- **BACKWARD INCOMPATIBLE** Type checking failures now raise
  ``typeguard.TypeCheckError`` instead of ``TypeError``
- Dropped Python 3.5 and 3.6 support
- Dropped the deprecated profiler hook (``TypeChecker``)
- Added a configuration system
- Added support for custom type checking functions
- Added support for PEP 604 union types (``X | Y``) on all Python versions
- Added support for generic built-in collection types (``list[int]`` et al) on all
  Python versions
- Added support for checking arbitrary ``Mapping`` types
- Added support for the ``Self`` type
- Added support for ``typing.Never`` (and ``typing_extensions.Never``)
- Added support for ``Never`` and ``NoReturn`` in argument annotations
- Added support for ``LiteralString``
- Added support for ``TypeGuard``
- Added support for the subclassable ``Any`` on Python 3.11 and ``typing_extensions``
- Added the possibility to have the import hook instrument all packages
- Added the ``suppress_type_checks()`` context manager function for temporarily
  disabling type checks
- Much improved error messages showing where the type check failed
- Made it possible to apply ``@typechecked`` on top of ``@classmethod`` /
  ``@staticmethod`` (PR by jacobpbrugh)
- Changed ``check_type()`` to return the passed value, so it can be used (to an extent)
  in place of ``typing.cast()``, but with run-time type checking
- Replaced custom implementation of ``is_typeddict()`` with the implementation from
  ``typing_extensions`` v4.1.0
- Emit ``InstrumentationWarning`` instead of raising ``RuntimeError`` from the pytest
  plugin if modules in the target package have already been imported
- Fixed ``TypeError`` when checking against ``TypedDict`` when the value has mixed types
  among the extra keys (PR by biolds)
- Fixed incompatibility with ``typing_extensions`` v4.1+ on Python 3.10 (PR by David C.)
- Fixed checking of ``Tuple[()]`` on Python 3.11 and ``tuple[()]`` on Python 3.9+
- Fixed integers 0 and 1 passing for ``Literal[False]`` and ``Literal[True]``,
  respectively
- Fixed type checking of annotated variable positional and keyword arguments (``*args``
  and ``**kwargs``)
- Fixed checks against ``unittest.Mock`` and derivatives being done in the wrong place

**2.13.3** (2021-12-10)

- Fixed ``TypeError`` when using typeguard within ``exec()`` (where ``__module__`` is ``None``)
  (PR by Andy Jones)
- Fixed ``TypedDict`` causing ``TypeError: TypedDict does not support instance and class checks``
  on Python 3.8 with standard library (not ``typing_extensions``) typed dicts

**2.13.2** (2021-11-23)

- Fixed ``typing_extensions`` being imported unconditionally on Python < 3.9
  (bug introduced in 2.13.1)

**2.13.1** (2021-11-23)

- Fixed ``@typechecked`` replacing abstract properties with regular properties
- Fixed any generic type subclassing ``Dict`` being mistakenly checked as ``TypedDict`` on
  Python 3.10

**2.13.0** (2021-10-11)

- Added support for returning ``NotImplemented`` from binary magic methods (``__eq__()`` et al)
- Added support for checking union types (e.g. ``Type[Union[X, Y]]``)
- Fixed error message when a check against a ``Literal`` fails in a union on Python 3.10
- Fixed ``NewType`` not being checked on Python 3.10
- Fixed unwarranted warning when ``@typechecked`` is applied to a class that contains unannotated
  properties
- Fixed ``TypeError`` in the async generator wrapper due to changes in ``__aiter__()`` protocol
- Fixed broken ``TypeVar`` checks – variance is now (correctly) disregarded, and only bound types
  and constraints are checked against (but type variable resolution is not done)

**2.12.1** (2021-06-04)

- Fixed ``AttributeError`` when ``__code__`` is missing from the checked callable (PR by epenet)

**2.12.0** (2021-04-01)

- Added ``@typeguard_ignore`` decorator to exclude specific functions and classes from
  runtime type checking (PR by Claudio Jolowicz)

**2.11.1** (2021-02-16)

- Fixed compatibility with Python 3.10

**2.11.0** (2021-02-13)

- Added support for type checking class properties (PR by Ethan Pronovost)
- Fixed static type checking of ``@typechecked`` decorators (PR by Kenny Stauffer)
- Fixed wrong error message when type check against a ``bytes`` declaration fails
- Allowed ``memoryview`` objects to pass as ``bytes`` (like MyPy does)
- Shortened tracebacks (PR by prescod)

**2.10.0** (2020-10-17)

- Added support for Python 3.9 (PR by Csergő Bálint)
- Added support for nested ``Literal``
- Added support for ``TypedDict`` inheritance (with some caveats; see the user guide on that for
  details)
- An appropriate ``TypeError`` is now raised when encountering an illegal ``Literal`` value
- Fixed checking ``NoReturn`` on Python < 3.8 when ``typing_extensions`` was not installed
- Fixed import hook matching unwanted modules (PR by Wouter Bolsterlee)
- Install the pytest plugin earlier in the test run to support more use cases
  (PR by Wouter Bolsterlee)

**2.9.1** (2020-06-07)

- Fixed ``ImportError`` on Python < 3.8 when ``typing_extensions`` was not installed

**2.9.0** (2020-06-06)

- Upped the minimum Python version from 3.5.2 to 3.5.3
- Added support for ``typing.NoReturn``
- Added full support for ``typing_extensions`` (now equivalent to support of the ``typing`` module)
- Added the option of supplying ``check_type()`` with globals/locals for correct resolution of
  forward references
- Fixed erroneous ``TypeError`` when trying to check against non-runtime ``typing.Protocol``
  (skips the check for now until a proper compatibility check has been implemented)
- Fixed forward references in ``TypedDict`` not being resolved
- Fixed checking against recursive types

**2.8.0** (2020-06-02)

- Added support for the ``Mock`` and ``MagicMock`` types (PR by prescod)
- Added support for ``typing_extensions.Literal`` (PR by Ryan Rowe)
- Fixed unintended wrapping of untyped generators (PR by prescod)
- Fixed checking against bound type variables with ``check_type()`` without a call memo
- Fixed error message when checking against a ``Union`` containing a ``Literal``

**2.7.1** (2019-12-27)

- Fixed ``@typechecked`` returning ``None`` when called with ``always=True`` and Python runs in
  optimized mode
- Fixed performance regression introduced in v2.7.0 (the ``getattr_static()`` call was causing a 3x
  slowdown)

**2.7.0** (2019-12-10)

- Added support for ``typing.Protocol`` subclasses
- Added support for ``typing.AbstractSet``
- Fixed the handling of ``total=False`` in ``TypedDict``
- Fixed no error reported on unknown keys with ``TypedDict``
- Removed support of default values in ``TypedDict``, as they are not supported in the spec

**2.6.1** (2019-11-17)

- Fixed import errors when using the import hook and trying to import a module that has both a
  module docstring and ``__future__`` imports in it
- Fixed ``AttributeError`` when using ``@typechecked`` on a metaclass
- Fixed ``@typechecked`` compatibility with built-in function wrappers
- Fixed type checking generator wrappers not being recognized as generators
- Fixed resolution of forward references in certain cases (inner classes, function-local classes)
- Fixed ``AttributeError`` when a class has contains a variable that is an instance of a class
  that has a ``__call__()`` method
- Fixed class methods and static methods being wrapped incorrectly when ``@typechecked`` is applied
  to the class
- Fixed ``AttributeError`` when ``@typechecked`` is applied to a function that has been decorated
  with a decorator that does not properly wrap the original (PR by Joel Beach)
- Fixed collections with mixed value (or key) types raising ``TypeError`` on Python 3.7+ when
  matched against unparametrized annotations from the ``typing`` module
- Fixed inadvertent ``TypeError`` when checking against a type variable that has constraints or
  a bound type expressed as a forward reference

**2.6.0** (2019-11-06)

- Added a :pep:`302` import hook for annotating functions and classes with ``@typechecked``
- Added a pytest plugin that activates the import hook
- Added support for ``typing.TypedDict``
- Deprecated ``TypeChecker`` (will be removed in v3.0)

**2.5.1** (2019-09-26)

- Fixed incompatibility between annotated ``Iterable``, ``Iterator``, ``AsyncIterable`` or
  ``AsyncIterator`` return types and generator/async generator functions
- Fixed ``TypeError`` being wrapped inside another TypeError (PR by russok)

**2.5.0** (2019-08-26)

- Added yield type checking via ``TypeChecker`` for regular generators
- Added yield, send and return type checking via ``@typechecked`` for regular and async generators
- Silenced ``TypeChecker`` warnings about async generators
- Fixed bogus ``TypeError`` on ``Type[Any]``
- Fixed bogus ``TypeChecker`` warnings when an exception is raised from a type checked function
- Accept a ``bytearray`` where ``bytes`` are expected, as per `python/typing#552`_
- Added policies for dealing with unmatched forward references
- Added support for using ``@typechecked`` as a class decorator
- Added ``check_return_type()`` to accompany ``check_argument_types()``
- Added Sphinx documentation

.. _python/typing#552: https://github.com/python/typing/issues/552

**2.4.1** (2019-07-15)

- Fixed broken packaging configuration

**2.4.0** (2019-07-14)

- Added :pep:`561` support
- Added support for empty tuples (``Tuple[()]``)
- Added support for ``typing.Literal``
- Make getting the caller frame faster (PR by Nick Sweeting)

**2.3.1** (2019-04-12)

- Fixed thread safety issue with the type hints cache (PR by Kelsey Francis)

**2.3.0** (2019-03-27)

- Added support for ``typing.IO`` and derivatives
- Fixed return type checking for coroutine functions
- Dropped support for Python 3.4

**2.2.2** (2018-08-13)

- Fixed false positive when checking a callable against the plain ``typing.Callable`` on Python 3.7

**2.2.1** (2018-08-12)

- Argument type annotations are no longer unioned with the types of their default values, except in
  the case of ``None`` as the default value (although PEP 484 still recommends against this)
- Fixed some generic types (``typing.Collection`` among others) producing false negatives on
  Python 3.7
- Shortened unnecessarily long tracebacks by raising a new ``TypeError`` based on the old one
- Allowed type checking against arbitrary types by removing the requirement to supply a call memo
  to ``check_type()``
- Fixed ``AttributeError`` when running with the pydev debugger extension installed
- Fixed getting type names on ``typing.*`` on Python 3.7 (fix by Dale Jung)

**2.2.0** (2018-07-08)

- Fixed compatibility with Python 3.7
- Removed support for Python 3.3
- Added support for ``typing.NewType`` (contributed by reinhrst)

**2.1.4** (2018-01-07)

- Removed support for backports.typing, as it has been removed from PyPI
- Fixed checking of the numeric tower (complex -> float -> int) according to PEP 484

**2.1.3** (2017-03-13)

- Fixed type checks against generic classes

**2.1.2** (2017-03-12)

- Fixed leak of function objects (should've used a ``WeakValueDictionary`` instead of
  ``WeakKeyDictionary``)
- Fixed obscure failure of TypeChecker when it's unable to find the function object
- Fixed parametrized ``Type`` not working with type variables
- Fixed type checks against variable positional and keyword arguments

**2.1.1** (2016-12-20)

- Fixed formatting of README.rst so it renders properly on PyPI

**2.1.0** (2016-12-17)

- Added support for ``typings.Type`` (available in Python 3.5.2+)
- Added a third, ``sys.setprofile()`` based type checking approach (``typeguard.TypeChecker``)
- Changed certain type error messages to display "function" instead of the function's qualified
  name

**2.0.2** (2016-12-17)

- More Python 3.6 compatibility fixes (along with a broader test suite)

**2.0.1** (2016-12-10)

- Fixed additional Python 3.6 compatibility issues

**2.0.0** (2016-12-10)

- **BACKWARD INCOMPATIBLE** Dropped Python 3.2 support
- Fixed incompatibility with Python 3.6
- Use ``inspect.signature()`` in place of ``inspect.getfullargspec``
- Added support for ``typing.NamedTuple``

**1.2.3** (2016-09-13)

- Fixed ``@typechecked`` skipping the check of return value type when the type annotation was
  ``None``

**1.2.2** (2016-08-23)

- Fixed checking of homogenous Tuple declarations (``Tuple[bool, ...]``)

**1.2.1** (2016-06-29)

- Use ``backports.typing`` when possible to get new features on older Pythons
- Fixed incompatibility with Python 3.5.2

**1.2.0** (2016-05-21)

- Fixed argument counting when a class is checked against a Callable specification
- Fixed argument counting when a functools.partial object is checked against a Callable
  specification
- Added checks against mandatory keyword-only arguments when checking against a Callable
  specification

**1.1.3** (2016-05-09)

- Gracefully exit if ``check_type_arguments`` can't find a reference to the current function

**1.1.2** (2016-05-08)

- Fixed TypeError when checking a builtin function against a parametrized Callable

**1.1.1** (2016-01-03)

- Fixed improper argument counting with bound methods when typechecking callables

**1.1.0** (2016-01-02)

- Eliminated the need to pass a reference to the currently executing function to
  ``check_argument_types()``

**1.0.2** (2016-01-02)

- Fixed types of default argument values not being considered as valid for the argument

**1.0.1** (2016-01-01)

- Fixed type hints retrieval being done for the wrong callable in cases where the callable was
  wrapped with one or more decorators

**1.0.0** (2015-12-28)

- Initial release
