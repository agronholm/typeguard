from __future__ import annotations

import sys
import warnings
from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Any, Callable, Iterable, NoReturn, TypeVar, cast, overload

from ._checkers import BINARY_MAGIC_METHODS, check_type_internal
from ._config import (
    CollectionCheckStrategy,
    ForwardRefPolicy,
    TypeCheckConfiguration,
    global_config,
)
from ._exceptions import TypeCheckError, TypeCheckWarning
from ._memo import TypeCheckMemo
from ._utils import qualified_name

if sys.version_info >= (3, 11):
    from typing import Literal, Never, TypeAlias
else:
    from typing_extensions import Literal, Never, TypeAlias

T = TypeVar("T")
TypeCheckFailCallback: TypeAlias = Callable[[TypeCheckError, TypeCheckMemo], Any]

type_checks_suppressed = 0
type_checks_suppress_lock = Lock()


@overload
def check_type(
    value: object,
    expected_type: type[T],
    *,
    forward_ref_policy: ForwardRefPolicy = ...,
    typecheck_fail_callback: TypeCheckFailCallback | None = ...,
    collection_check_strategy: CollectionCheckStrategy = ...,
) -> T:
    ...


@overload
def check_type(
    value: object,
    expected_type: Any,
    *,
    forward_ref_policy: ForwardRefPolicy = ...,
    typecheck_fail_callback: TypeCheckFailCallback | None = ...,
    collection_check_strategy: CollectionCheckStrategy = ...,
) -> Any:
    ...


def check_type(
    value: object,
    expected_type: Any,
    *,
    forward_ref_policy: ForwardRefPolicy = TypeCheckConfiguration().forward_ref_policy,
    typecheck_fail_callback: (TypeCheckFailCallback | None) = (
        TypeCheckConfiguration().typecheck_fail_callback
    ),
    collection_check_strategy: CollectionCheckStrategy = (
        TypeCheckConfiguration().collection_check_strategy
    ),
) -> Any:
    """
    Ensure that ``value`` matches ``expected_type``.

    The types from the :mod:`typing` module do not support :func:`isinstance` or
    :func:`issubclass` so a number of type specific checks are required. This function
    knows which checker to call for which type.

    This function wraps :func:`~.check_type_internal` in the following ways:

    * Respects type checking suppression (:func:`~.suppress_type_checks`)
    * Forms a :class:`~.TypeCheckMemo` from the current stack frame
    * Calls the configured type check fail callback if the check fails

    Note that this function is independent of the globally shared configuration in
    :data:`typeguard.config`. This means that usage within libraries is safe from being
    affected configuration changes made by other libraries or by the integrating
    application. Instead, configuration options have the same default values as their
    corresponding fields in :class:`TypeCheckConfiguration`.

    :param value: value to be checked against ``expected_type``
    :param expected_type: a class or generic type instance
    :param forward_ref_policy: see :attr:`TypeCheckConfiguration.forward_ref_policy`
    :param typecheck_fail_callback:
        see :attr`TypeCheckConfiguration.typecheck_fail_callback`
    :param collection_check_strategy:
        see :attr:`TypeCheckConfiguration.collection_check_strategy`
    :return: ``value``, unmodified
    :raises TypeCheckError: if there is a type mismatch

    """
    config = TypeCheckConfiguration(
        forward_ref_policy=forward_ref_policy,
        typecheck_fail_callback=typecheck_fail_callback,
        collection_check_strategy=collection_check_strategy,
    )

    if type_checks_suppressed or expected_type is Any:
        return

    frame = sys._getframe(1)
    memo = TypeCheckMemo(frame.f_globals, frame.f_locals)
    try:
        check_type_internal(value, expected_type, memo, config)
    except TypeCheckError as exc:
        exc.append_path_element(qualified_name(value, add_class_prefix=True))
        if config.typecheck_fail_callback:
            config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return value


def check_argument_types(
    func_name: str,
    arguments: dict[str, tuple[Any, Any]],
    # vararg: tuple[str, tuple[object, ...], Any] | None,
    # kwarg: tuple[str, dict[str, object], Any] | None,
    memo: TypeCheckMemo,
) -> Literal[True]:
    if type_checks_suppressed:
        return True

    # if vararg:
    #     arguments[vararg[0]] = vararg[1], Tuple[vararg[2]]
    #
    # if kwarg:
    #     arguments[kwarg[0]] = vararg[1], Dict[str, vararg[2]]

    for argname, (value, annotation) in arguments.items():
        if annotation is NoReturn or annotation is Never:
            exc = TypeCheckError(
                f"{func_name}() was declared never to be called but it was"
            )
            if global_config.typecheck_fail_callback:
                global_config.typecheck_fail_callback(exc, memo)
            else:
                raise exc

        try:
            check_type_internal(value, annotation, memo, global_config)
        except TypeCheckError as exc:
            qualname = qualified_name(value, add_class_prefix=True)
            exc.append_path_element(f'argument "{argname}" ({qualname})')
            if global_config.typecheck_fail_callback:
                global_config.typecheck_fail_callback(exc, memo)
            else:
                raise

    return True


def check_return_type(
    func_name: str, retval: T, annotation: Any, memo: TypeCheckMemo
) -> T:
    if type_checks_suppressed:
        return retval

    if annotation is NoReturn or annotation is Never:
        exc = TypeCheckError(f"{func_name}() was declared never to return but it did")
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise exc

    try:
        check_type_internal(retval, annotation, memo, global_config)
    except TypeCheckError as exc:
        # Allow NotImplemented if this is a binary magic method (__eq__() et al)
        if retval is NotImplemented and annotation is bool:
            # This does (and cannot) not check if it's actually a method
            func_name = func_name.rsplit(".", 1)[-1]
            if func_name in BINARY_MAGIC_METHODS:
                return retval

        qualname = qualified_name(retval, add_class_prefix=True)
        exc.append_path_element(f"the return value ({qualname})")
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return retval


def check_send_type(
    func_name: str, sendval: T, annotation: Any, memo: TypeCheckMemo
) -> T:
    if type_checks_suppressed:
        return sendval

    if annotation is NoReturn or annotation is Never:
        exc = TypeCheckError(
            f"{func_name}() was declared never to be sent a value to but it was"
        )
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise exc

    try:
        check_type_internal(sendval, annotation, memo, global_config)
    except TypeCheckError as exc:
        qualname = qualified_name(sendval, add_class_prefix=True)
        exc.append_path_element(f"the value sent to generator ({qualname})")
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return sendval


def check_yield_type(
    func_name: str, yieldval: T, annotation: Any, memo: TypeCheckMemo
) -> T:
    if type_checks_suppressed:
        return yieldval

    if annotation is NoReturn or annotation is Never:
        exc = TypeCheckError(f"{func_name}() was declared never to yield but it did")
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise exc

    try:
        check_type_internal(yieldval, annotation, memo, global_config)
    except TypeCheckError as exc:
        qualname = qualified_name(yieldval, add_class_prefix=True)
        exc.append_path_element(f"the yielded value ({qualname})")
        if global_config.typecheck_fail_callback:
            global_config.typecheck_fail_callback(exc, memo)
        else:
            raise

    return yieldval


def check_variable_assignment(
    value: object, expected_annotations: dict[str, Any], memo: TypeCheckMemo
) -> Any:
    if type_checks_suppressed:
        return

    if len(expected_annotations) > 1:
        source_values = cast("Iterable[Any]", value)
    else:
        source_values = (value,)

    iterated_values = []
    for obj, (argname, expected_type) in zip(
        source_values, expected_annotations.items()
    ):
        iterated_values.append(obj)
        try:
            check_type_internal(obj, expected_type, memo, global_config)
        except TypeCheckError as exc:
            exc.append_path_element(argname)
            if global_config.typecheck_fail_callback:
                global_config.typecheck_fail_callback(exc, memo)
            else:
                raise

    return iterated_values if len(iterated_values) > 1 else iterated_values[0]


def warn_on_error(exc: TypeCheckError, memo: TypeCheckMemo) -> None:
    """
    Emit a warning on a type mismatch.

    This is intended to be used as an error handler in
    :attr:`TypeCheckConfiguration.typecheck_fail_callback`.

    """
    warnings.warn(TypeCheckWarning(str(exc)), stacklevel=3)


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
