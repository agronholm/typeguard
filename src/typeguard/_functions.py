from __future__ import annotations

import sys
import warnings
from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Any, Callable, NoReturn, TypeVar, overload

from ._checkers import BINARY_MAGIC_METHODS, check_type_internal
from ._config import global_config
from ._exceptions import TypeCheckError, TypeCheckWarning
from ._memo import CallMemo, TypeCheckMemo
from ._utils import get_stacklevel, qualified_name

if sys.version_info >= (3, 11):
    from typing import Never
else:
    from typing_extensions import Never

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

T = TypeVar("T")
TypeCheckFailCallback: TypeAlias = Callable[[TypeCheckError, TypeCheckMemo], Any]

type_checks_suppressed = 0
type_checks_suppress_lock = Lock()


@overload
def check_type(value: object, expected_type: type[T]) -> T:
    ...


@overload
def check_type(value: object, expected_type: Any) -> Any:
    ...


def check_type(value: object, expected_type: Any) -> Any:
    """
    Ensure that ``value`` matches ``expected_type``.

    The types from the :mod:`typing` module do not support :func:`isinstance` or
    :func:`issubclass` so a number of type specific checks are required. This function
    knows which checker to call for which type.

    This function wraps :func:`~.check_type_internal` in the following ways:

    * Respects type checking suppression (:func:`~.suppress_type_checks`)
    * Forms a :class:`~.TypeCheckMemo` from the current stack frame
    * Calls the configured type check fail callback if the check fails

    :param value: value to be checked against ``expected_type``
    :param expected_type: a class or generic type instance
    :return: ``value``, unmodified
    :raises TypeCheckError: if there is a type mismatch

    """
    if type_checks_suppressed or expected_type is Any:
        return

    frame = sys._getframe(1)
    memo = TypeCheckMemo(frame.f_globals, frame.f_locals)
    try:
        check_type_internal(value, expected_type, memo)
    except TypeCheckError as exc:
        exc.append_path_element(qualified_name(value, add_class_prefix=True))
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return value


def check_argument_types(memo: CallMemo) -> Literal[True]:
    """
    Check that the argument values match the annotated types.

    This should be called first thing within the body of a type annotated function.
    If ``memo`` is not provided, the information will be retrieved from the previous
    stack frame (ie. from the function that called this).

    :return: ``True``
    :raises TypeError: if there is an argument type mismatch

    """
    if type_checks_suppressed:
        return True

    for argname, expected_type in memo.type_hints.items():
        if argname != "return" and argname in memo.arguments:
            if expected_type is NoReturn or expected_type is Never:
                exc = TypeCheckError(
                    f"{memo.func_name}() was declared never to be called but it was"
                )
                if global_config.typecheck_fail_callback:
                    global_config.typecheck_fail_callback(exc, memo)
                else:
                    raise exc

            value = memo.arguments[argname]
            try:
                check_type_internal(value, expected_type, memo=memo)
            except TypeCheckError as exc:
                qualname = qualified_name(value, add_class_prefix=True)
                exc.append_path_element(f'argument "{argname}" ({qualname})')
                if global_config.typecheck_fail_callback:
                    global_config.typecheck_fail_callback(exc, memo)
                else:
                    raise

    return True


def check_return_type(retval: T, memo: CallMemo) -> T:
    """
    Check that the return value is compatible with the return value annotation in the
    function.

    This should be used to wrap the return statement, as in::

        # Before
        return "foo"
        # After
        return check_return_type("foo")

    :param retval: the value that should be returned from the call
    :return: ``retval``, unmodified
    :raises TypeCheckError: if there is a type mismatch

    """
    if type_checks_suppressed:
        return retval

    if "return" in memo.type_hints:
        annotation = memo.type_hints["return"]
        if annotation is NoReturn or annotation is Never:
            exc = TypeCheckError(
                f"{memo.func_name}() was declared never to return but it did"
            )
            if global_config.typecheck_fail_callback:
                global_config.typecheck_fail_callback(exc, memo)
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
                    return retval

            qualname = qualified_name(retval, add_class_prefix=True)
            exc.append_path_element(f"the return value ({qualname})")
            if global_config.typecheck_fail_callback:
                global_config.typecheck_fail_callback(exc, memo)
            else:
                raise

    return retval


def check_send_type(sendval: T, memo: CallMemo) -> T:
    if type_checks_suppressed:
        return sendval

    annotation = memo.type_hints[":send"]
    if annotation is NoReturn or annotation is Never:
        exc = TypeCheckError(
            f"{memo.func_name}() was declared never to be sent a value to but it was"
        )
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise exc

    try:
        check_type_internal(sendval, annotation, memo)
    except TypeCheckError as exc:
        qualname = qualified_name(sendval, add_class_prefix=True)
        exc.append_path_element(f"the value sent to generator ({qualname})")
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return sendval


def check_yield_type(yieldval: T, memo: CallMemo) -> T:
    """
    Check that the yielded value is compatible with the generator return value
    annotation in the function.

    This should be used to wrap a ``yield`` statement, as in::

        # Before
        yield "foo"
        # After
        yield check_yield_value("foo")

    :param yieldval: the value that should be yielded from the generator
    :return: ``yieldval``, unmodified
    :raises TypeCheckError: if there is a type mismatch

    """
    if type_checks_suppressed:
        return yieldval

    if "yield" in memo.type_hints:
        annotation = memo.type_hints["yield"]
        if annotation is NoReturn or annotation is Never:
            exc = TypeCheckError(
                f"{memo.func_name}() was declared never to yield but it did"
            )
            if global_config.typecheck_fail_callback:
                global_config.typecheck_fail_callback(exc, memo)
            else:
                raise exc

        try:
            check_type_internal(yieldval, annotation, memo)
        except TypeCheckError as exc:
            qualname = qualified_name(yieldval, add_class_prefix=True)
            exc.append_path_element(f"the yielded value ({qualname})")
            if global_config.typecheck_fail_callback:
                global_config.typecheck_fail_callback(exc, memo)
            else:
                raise

    return yieldval


def check_variable_assignment(
    value: object, varname: str, annotation: Any, memo: CallMemo
) -> Any:
    if type_checks_suppressed:
        return

    try:
        check_type_internal(value, annotation, memo)
    except TypeCheckError as exc:
        qualname = qualified_name(value, add_class_prefix=True)
        exc.append_path_element(f"value assigned to {varname} ({qualname})")
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return value


def check_multi_variable_assignment(
    value: Any, targets: list[dict[str, Any]], memo: CallMemo
) -> Any:
    if type_checks_suppressed:
        return

    if max(len(target) for target in targets) == 1:
        iterated_values = [value]
    else:
        iterated_values = list(value)

    for expected_types in targets:
        value_index = 0
        for ann_index, (varname, expected_type) in enumerate(expected_types.items()):
            if varname.startswith("*"):
                varname = varname[1:]
                keys_left = len(expected_types) - 1 - ann_index
                next_value_index = len(iterated_values) - keys_left
                obj: object = iterated_values[value_index:next_value_index]
                value_index = next_value_index
            else:
                obj = iterated_values[value_index]
                value_index += 1

            try:
                check_type_internal(obj, expected_type, memo)
            except TypeCheckError as exc:
                qualname = qualified_name(obj, add_class_prefix=True)
                exc.append_path_element(f"value assigned to {varname} ({qualname})")
                if global_config.typecheck_fail_callback:
                    global_config.typecheck_fail_callback(exc, memo)
                else:
                    raise

    return iterated_values[0] if len(iterated_values) == 1 else iterated_values


def warn_on_error(exc: TypeCheckError, memo: TypeCheckMemo) -> None:
    """
    Emit a warning on a type mismatch.

    This is intended to be used as an error handler in
    :attr:`TypeCheckConfiguration.typecheck_fail_callback`.

    """
    warnings.warn(TypeCheckWarning(str(exc)), stacklevel=get_stacklevel())


@contextmanager
def suppress_type_checks() -> Generator[None, None, None]:
    """
    A context manager that can be used to temporarily suppress type checks.

    While this context manager is active, :func:`check_type` and any automatically
    instrumented functions skip the actual type checking. These context managers can be
    nested. Type checking will resume once the last context manager block is exited.

    This context manager is thread-safe.

    """
    global type_checks_suppressed

    with type_checks_suppress_lock:
        type_checks_suppressed += 1

    yield

    with type_checks_suppress_lock:
        type_checks_suppressed -= 1
