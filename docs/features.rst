Features
=========

.. py:currentmodule:: typeguard

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
* ``ParamSpec`` is currently ignored

Other limitations
-----------------

Non-local forward references
++++++++++++++++++++++++++++

Forward references pointing to non-local types (class defined inside a function, and a
nested function within the same parent function referring to that class) cannot
currently be resolved::

    def outer():
        class Inner:
            pass

        instance = Inner()

        # Inner cannot be resolved because it is not in the __globals__ of inner() or
        # its closure
        def inner() -> "Inner":
            return instance

        return inner()

However, if you explicitly reference the type in the nested function, that will work::

        # Inner is part of the closure of inner() now so it can be resolved
        def inner() -> "Inner":
            return Inner()

A similar corner case would be a forward reference to a nested class::

    class Outer:
        class Inner:
            pass

        # Cannot be resolved as the name is no longer available
        def method() -> "Inner":
            return Outer.Inner()

Both these shortcomings may be resolved in a future release.

Using :func:`@typechecked <typechecked>` on top of other decorators
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

As :func:`@typechecked <typechecked>` works by recompiling the target function with
instrumentation added, it needs to replace all the references to the original function
with the new one. This could be impossible when it's placed on top of another decorator
that wraps the original function. It has no way of telling that other decorator that the
target function should be switched to a new one. To work around this limitation, either
place :func:`@typechecked <typechecked>` at the bottom of the decorator stack, or use
the import hook instead.

Special considerations for ``if TYPE_CHECKING:``
------------------------------------------------

Both the import hook and :func:`@typechecked <typechecked>` avoid checking against
anything imported in a module-level ``if TYPE_CHECKING:`` (or
``if typing.TYPE_CHECKING:``) block, since those types will not be available at run
time. Therefore, no errors or warnings are emitted for such annotations, even when they
would normally not be found.

Support for generator functions
-------------------------------

For generator functions, the checks applied depend on the function's return annotation.
For example, the following function gets its yield, send and return values type
checked::

    from collections.abc import Generator

    def my_generator() -> Generator[int, str, bool]:
        a = yield 6
        return True

In contrast, the following generator function only gets its yield value checked::

    from collections.abc import Iterator

    def my_generator() -> Iterator[int]:
        a = yield 6
        return True

Asynchronous generators work just the same way, except they don't support returning
values other than ``None``, so the annotation only has two items::

    from collections.abc import AsyncGenerator

    async def my_generator() -> AsyncGenerator[int, str]:
        a = yield 6

Overall, the following type annotations will work for generator function type checking:

* :class:`typing.Generator`
* :class:`collections.abc.Generator`
* :class:`typing.Iterator`
* :class:`collections.abc.Iterator`
* :class:`typing.Iterable`
* :class:`collections.abc.Iterable`
* :class:`typing.AsyncIterator`
* :class:`collections.abc.AsyncIterator`
* :class:`typing.AsyncIterable`
* :class:`collections.abc.AsyncIterable`
* :class:`typing.AsyncGenerator`
* :class:`collections.abc.AsyncGenerator`

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
