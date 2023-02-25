Features
=========

What does Typeguard check?
--------------------------

The following type checks are implemented in Typeguard:

* Types of arguments passed to instrumented functions
* Types of values returned from instrumented functions
* Types of values yielded from instrumented generator functions
* Types of values sent to instrumented generator functions
* Types of values assigned to local variables within instrumented functions

What does Typeguard NOT check?
------------------------------

The following type checks are not yet supported in Typeguard:

* Types of values assigned to class or instance variables
* Types of values assigned to global or nonlocal variables
* Stubs defined with :func:`@overload <typing.overload>` (the implementation is checked
  if instrumented)
* ``yield_from`` statements in generator functions

Support for PEP 604 unions on Pythons older than 3.10
-----------------------------------------------------

The :pep:`604` ``X | Y`` notation was introduced in Python 3.10, but it can be used with
older Python versions in modules where ``from __future__ import annotations`` is
present. Typeguard contains a special parser that lets it convert these to older
:class:`~typing.Union` annotations internally.

Support for generic built-in collection types on Pythons older than 3.9
-----------------------------------------------------------------------

The built-in collection types (:class:`list`, :class:`tuple`, :class:`dict`,
:class:`set` and :class:`frozenset`) gained support for generics in Python 3.9.
For earlier Python versions, Typeguard provides a way to work with such annotations by
substituting them with the equivalent :mod:`typing` types. The only requirement for this
to work is the use of ``from __future__ import annotations`` in all such modules.

Support for mock objects
------------------------

Typeguard handles the :class:`unittest.mock.Mock` class (and its subclasses) specially,
bypassing any type checks when encountering instances of these classes. Note that any
"spec" class passed to the mock object is currently not respected.

Supported standard library annotations
--------------------------------------

The following types from the standard library have specialized support:

.. list-table::
   :header-rows: 1

   * - Type(s)
     - Notes
   * - :class:`typing.Any`
     - Any type passes type checks against this annotation. Inheriting from ``Any``
       (:class:`typing.Any` on Python 3.11+, or ``typing.extensions.Any``) will pass any
       type check
   * - :class:`typing.Annotated`
     - Original annotation is unwrapped and typechecked normally
   * - :class:`BinaryIO`
     - Specialized instance checks are performed
   * - | :class:`typing.Callable`
       | :class:`collections.abc.Callable`
     - Argument count is checked but types are not (yet)
   * - | :class:`dict`
       | :class:`typing.Dict`
     - Keys and values are typechecked
   * - :class:`typing.IO`
     - Specialized instance checks are performed
   * - | :class:`list`
       | :class:`typing.List`
     - Contents are typechecked
   * - :class:`typing.Literal`
     -
   * - :class:`typing.LiteralString`
     - Checked as :class:`str`
   * - | :class:`typing.Mapping`
       | :class:`typing.MutableMapping`
       | :class:`collections.abc.Mapping`
       | :class:`collections.abc.MutableMapping`
     - Keys and values are typechecked
   * - :class:`typing.NamedTuple`
     - Field values are typechecked
   * - | :class:`typing.Never`
       | :class:`typing.NoReturn`
     - Supported in argument and return type annotations
   * - :class:`typing.Protocol`
     - Run-time protocols are checked with :func:`isinstance`, others are ignored
   * - :class:`typing.Self`
     -
   * - | :class:`set`
       | :class:`frozenset`
       | :class:`typing.Set`
       | :class:`typing.AbstractSet`
     - Contents are typechecked
   * - | :class:`typing.Sequence`
       | :class:`collections.abc.Sequence`
     - Contents are typechecked
   * - :class:`typing.TextIO`
     - Specialized instance checks are performed
   * - | :class:`tuple`
       | :class:`typing.Tuple`
     - Contents are typechecked
   * - | :class:`type`
       | :class:`typing.Type`
     -
   * - :class:`typing.TypeGuard`
     - Checked as :class:`bool`
   * - :class:`typing.TypedDict`
     - Contents are typechecked; On Python 3.8 and earlier, ``total`` from superclasses
       is not respected (see `#101`_ for more information); On Python 3.9.0, false
       positives can happen when constructing :class:`typing.TypedDict` classes using
       old-style syntax (see `issue 42059`_)
   * - :class:`typing.TypeVar`
     - Constraints and bound types are typechecked
   * - :class:`typing.Union`
     - :pep:`604` unions are supported on all Python versions when
       ``from __future__ import annotations`` is used

.. _#101: https://github.com/agronholm/typeguard/issues/101
.. _issue 42059: https://bugs.python.org/issue42059
