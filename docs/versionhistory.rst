Version history
===============

This library adheres to
`Semantic Versioning 2.0 <https://semver.org/#semantic-versioning-200>`_.

**UNRELEASED**

- Fixed a ``Protocol`` member declared as a ``property`` being skipped by the checker
  entirely, so a value that did not have that attribute at all was accepted
  (`#598 <https://github.com/agronholm/typeguard/pull/598>`_; PR by @feiiiiii5)
- Fixed an exception other than ``AttributeError`` raised while reading a ``Protocol``
  member (a ``__getattr__`` that raises, or a property whose getter raises) escaping
  ``check_type()`` instead of being reported as ``TypeCheckError``
  (`#598 <https://github.com/agronholm/typeguard/pull/598>`_; PR by @feiiiiii5)
- Fixed empty ``NamedTuple`` annotations accepting unrelated tuple instances
  (`#614 <https://github.com/agronholm/typeguard/issues/614>`_; PR by @parijat1222q)
- Fixed ``check_return_type()`` raising a bare ``KeyError: 'return'`` when used
  inside a function without a return annotation; it now skips the check, matching
  how ``check_argument_types()`` treats unannotated parameters
  (`#609 <https://github.com/agronholm/typeguard/pull/609>`_; PR by @feiiiiii5)
- Fixed a false ``TypeCheckError`` (or a leaked ``ValueError`` from a custom
  ``__eq__``) when checking a callable whose keyword-only parameters have default
  values, caused by comparing the default to ``Parameter.empty`` with ``==`` instead
  of ``is`` (`#608 <https://github.com/agronholm/typeguard/pull/608>`_; PR by @feiiiiii5)

**4.6.1** (2026-11-19)

- Fixed documentation builds failing on references to removed typing APIs and older
  typing object kinds by adding a legacy Python documentation inventory
  (`#612 <https://github.com/agronholm/typeguard/issues/612>`_; PR by @parijat1222q)
- Fixed ``ReadOnly`` (:pep:`705`) qualifiers on ``TypedDict`` items being left
  unwrapped, which caused the item's value type to skip type checking entirely
  (`#571 <https://github.com/agronholm/typeguard/pull/571>`_; PR by @jaideeppyne)
- Added the ``TypeCheckError.memo`` attribute containing the memo from the failed check
  (`#579 <https://github.com/agronholm/typeguard/pull/579>`_; PR by @alex-c-s)
- Fixed ``ForwardRef`` instances not being evaluated against the target's module
  namespace in argument type checks with ``from __future__ import annotations``
  (`#576 <https://github.com/agronholm/typeguard/issues/576>`_; PR by @alex-c-s)
