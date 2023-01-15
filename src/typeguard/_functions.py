from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Any, NoReturn, TypeVar, overload
from unittest.mock import Mock

from ._checkers import BINARY_MAGIC_METHODS, check_type_internal
from ._exceptions import TypeCheckError
from ._memo import CallMemo, TypeCheckMemo
from ._utils import find_function

if sys.version_info >= (3, 11):
    from typing import Never
else:
    from typing_extensions import Never

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

T = TypeVar("T")
type_checks_suppressed = 0
type_checks_suppress_lock = Lock()


@overload
def check_type(
    value: object,
    expected_type: type[T],
    *,
    argname: str = "value",
    memo: TypeCheckMemo | None = None,
) -> T:
    ...


@overload
def check_type(
    value: object,
    expected_type: Any,
    *,
    argname: str = "value",
    memo: TypeCheckMemo | None = None,
) -> Any:
    ...


def check_type(
    value: object,
    expected_type: Any,
    *,
    argname: str = "value",
    memo: TypeCheckMemo | None = None,
) -> Any:
    """
    Ensure that ``value`` matches ``expected_type``.

    The types from the :mod:`typing` module do not support :func:`isinstance` or
    :func:`issubclass` so a number of type specific checks are required. This function
    knows which checker to call for which type.

    :param value: value to be checked against ``expected_type``
    :param expected_type: a class or generic type instance
    :param argname: name of the argument to check; used for error messages
    :return: ``value``, unmodified
    :raises TypeCheckError: if there is a type mismatch

    """
    if type_checks_suppressed or expected_type is Any or isinstance(value, Mock):
        return

    if memo is None:
        frame = sys._getframe(1)
        memo = TypeCheckMemo(frame.f_globals, frame.f_locals)

    try:
        check_type_internal(value, expected_type, memo)
    except TypeCheckError as exc:
        exc.append_path_element(argname)
        if memo.config.typecheck_fail_callback:
            memo.config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return value


def check_argument_types(memo: CallMemo | None = None) -> Literal[True]:
    """
    Check that the argument values match the annotated types.

    Unless both ``args`` and ``kwargs`` are provided, the information will be retrieved
    from the previous stack frame (ie. from the function that called this).

    :return: ``True``
    :raises TypeError: if there is an argument type mismatch

    """
    if type_checks_suppressed:
        return True

    if memo is None:
        # faster than inspect.currentframe(), but not officially
        # supported in all python implementations
        frame = sys._getframe(1)

        try:
            func = find_function(frame)
        except LookupError:
            # This can happen with the Pydev/PyCharm debugger extension installed
            return True

        memo = CallMemo(func, frame.f_locals)

    for argname, expected_type in memo.type_hints.items():
        if argname != "return" and argname in memo.arguments:
            if expected_type is NoReturn or expected_type is Never:
                exc = TypeCheckError(
                    f"{memo.func_name}() was declared never to be called but it was"
                )
                if memo.config.typecheck_fail_callback:
                    memo.config.typecheck_fail_callback(exc, memo)
                else:
                    raise exc

            value = memo.arguments[argname]
            try:
                check_type_internal(value, expected_type, memo=memo)
            except TypeCheckError as exc:
                exc.append_path_element(f'argument "{argname}"')
                if memo.config.typecheck_fail_callback:
                    memo.config.typecheck_fail_callback(exc, memo)
                else:
                    raise

    return True


def check_return_type(retval: T, memo: CallMemo | None = None) -> TypeGuard[T]:
    """
    Check that the return value is compatible with the return value annotation in the
    function.

    :param retval: the value about to be returned from the call
    :return: ``True``
    :raises TypeError: if there is a type mismatch

    """
    if type_checks_suppressed:
        return True

    if memo is None:
        # faster than inspect.currentframe(), but not officially
        # supported in all python implementations
        frame = sys._getframe(1)

        try:
            func = find_function(frame)
        except LookupError:
            # This can happen with the Pydev/PyCharm debugger extension installed
            return True

        memo = CallMemo(func, frame.f_locals)

    if "return" in memo.type_hints:
        annotation = memo.type_hints["return"]
        if annotation is NoReturn or annotation is Never:
            exc = TypeCheckError(
                f"{memo.func_name}() was declared never to return but it did"
            )
            if memo.config.typecheck_fail_callback:
                memo.config.typecheck_fail_callback(exc, memo)
            else:
                raise exc

        try:
            check_type_internal(retval, annotation, memo)
        except TypeCheckError as exc:
            # Allow NotImplemented if this is a binary magic method (__eq__() et al)
            if retval is NotImplemented and annotation is bool:
                # This does (and cannot) not check if it's actually a method
                func_name = memo.func_name.rsplit(".", 1)[-1]
                if len(memo.arguments) == 2 and func_name in BINARY_MAGIC_METHODS:
                    return True

            exc.append_path_element("the return value")
            if memo.config.typecheck_fail_callback:
                memo.config.typecheck_fail_callback(exc, memo)
            else:
                raise

    return True


@contextmanager
def suppress_type_checks() -> Generator[None, None, None]:
    """
    A context manager that can be used to temporarily suppress type checks.

    While this context manager is active, :func:`check_argument_types`,
    :func:`check_return_type`, :func:`@typechecked <typechecked>` and :func:`check_type`
    all skip the actual type checking. These context managers can be nested. Type
    checking will resume once the last context manager block is exited.

    This context manager is thread-safe.

    """
    global type_checks_suppressed

    with type_checks_suppress_lock:
        type_checks_suppressed += 1

    yield

    with type_checks_suppress_lock:
        type_checks_suppressed -= 1
