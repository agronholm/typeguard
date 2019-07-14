Version history
===============

This library adheres to `Semantic Versioning 2.0 <https://semver.org/#semantic-versioning-200>`_.

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
