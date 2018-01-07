Version history
===============

This library adheres to `Semantic Versioning <http://semver.org/>`_.

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
