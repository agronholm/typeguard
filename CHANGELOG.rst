Version history
===============

1.2.0
-----

- Fixed argument counting when a class is checked against a Callable specification
- Fixed argument counting when a functools.partial object is checked against a Callable
  specification
- Added checks against mandatory keyword-only arguments when checking against a Callable
  specification


1.1.3
-----

- Gracefully exit if ``check_type_arguments`` can't find a reference to the current function


1.1.2
-----

- Fixed TypeError when checking a builtin function against a parametrized Callable


1.1.1
-----

- Fixed improper argument counting with bound methods when typechecking callables


1.1.0
-----

- Eliminated the need to pass a reference to the currently executing function to
  ``check_argument_types()``


1.0.2
-----

- Fixed types of default argument values not being considered as valid for the argument


1.0.1
-----

- Fixed type hints retrieval being done for the wrong callable in cases where the callable was
  wrapped with one or more decorators


1.0.0
-----

- Initial release
