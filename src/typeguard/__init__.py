__all__ = (
    "CallMemo",
    "ForwardRefPolicy",
    "TypeCheckerCallable",
    "TypeCheckLookupCallback",
    "TypeCheckConfiguration",
    "TypeHintWarning",
    "TypeCheckWarning",
    "TypeCheckError",
    "TypeCheckMemo",
    "check_argument_types",
    "check_return_type",
    "check_type",
    "config",
    "typechecked",
    "typeguard_ignore",
    "warn_on_error",
)

import inspect
import sys
from functools import partial, wraps
from inspect import isasyncgen, isclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    NoReturn,
    Optional,
    TypeVar,
    overload,
)
from unittest.mock import Mock
from warnings import warn

from ._checkers import (
    BINARY_MAGIC_METHODS,
    TypeCheckerCallable,
    TypeCheckLookupCallback,
    check_type_internal,
)
from ._config import ForwardRefPolicy, TypeCheckConfiguration, warn_on_error
from ._exceptions import TypeCheckError, TypeCheckWarning, TypeHintWarning
from ._generators import (
    TypeCheckedAsyncGenerator,
    TypeCheckedGenerator,
    asyncgen_origin_types,
    generator_origin_types,
)
from ._memo import CallMemo, TypeCheckMemo
from ._utils import find_function, function_name

if TYPE_CHECKING:
    _F = TypeVar("_F")

    def typeguard_ignore(f: _F) -> _F:
        """This decorator is a noop during static type-checking."""
        return f

else:
    from typing import no_type_check as typeguard_ignore

config = TypeCheckConfiguration()

T_CallableOrType = TypeVar("T_CallableOrType", bound=Callable[..., Any])


def check_type(
    value: Any,
    expected_type: Any,
    *,
    argname: str = "value",
    memo: Optional[TypeCheckMemo] = None,
) -> None:
    """
    Ensure that ``value`` matches ``expected_type``.

    The types from the :mod:`typing` module do not support :func:`isinstance` or
    :func:`issubclass` so a number of type specific checks are required. This function
    knows which checker to call for which type.

    :param value: value to be checked against ``expected_type``
    :param expected_type: a class or generic type instance
    :param argname: name of the argument to check; used for error messages
    :raises TypeCheckError: if there is a type mismatch

    """
    if expected_type is Any or isinstance(value, Mock):
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


def check_argument_types(memo: Optional[CallMemo] = None) -> bool:
    """
    Check that the argument values match the annotated types.

    Unless both ``args`` and ``kwargs`` are provided, the information will be retrieved
    from the previous stack frame (ie. from the function that called this).

    :return: ``True``
    :raises TypeError: if there is an argument type mismatch

    """
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


def check_return_type(retval, memo: Optional[CallMemo] = None) -> bool:
    """
    Check that the return value is compatible with the return value annotation in the
    function.

    :param retval: the value about to be returned from the call
    :return: ``True``
    :raises TypeError: if there is a type mismatch

    """
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
        if memo.type_hints["return"] is NoReturn:
            raise TypeCheckError(
                f"{memo.func_name}() was declared never to return but it did"
            )

        try:
            check_type_internal(retval, memo.type_hints["return"], memo)
        except TypeCheckError as exc:
            # Allow NotImplemented if this is a binary magic method (__eq__() et al)
            if retval is NotImplemented and memo.type_hints["return"] is bool:
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


@overload
def typechecked(
    *, always: bool = False
) -> Callable[[T_CallableOrType], T_CallableOrType]:
    ...


@overload
def typechecked(func: T_CallableOrType, *, always: bool = False) -> T_CallableOrType:
    ...


def typechecked(func=None, *, always=False, _localns: Optional[Dict[str, Any]] = None):
    """
    Perform runtime type checking on the arguments that are passed to the wrapped
    function.

    The return value is also checked against the return annotation if any.

    If the ``__debug__`` global variable is set to ``False``, no wrapping and therefore
    no type checking is done, unless ``always`` is ``True``.

    This can also be used as a class decorator. This will wrap all type annotated
    methods, including ``@classmethod``, ``@staticmethod``,  and ``@property``
    decorated methods, in the class with the ``@typechecked`` decorator.

    :param func: the function or class to enable type checking for
    :param always: ``True`` to enable type checks even in optimized mode

    """
    if func is None:
        return partial(typechecked, always=always, _localns=_localns)

    if not __debug__ and not always:  # pragma: no cover
        return func

    if isclass(func):
        prefix = func.__qualname__ + "."
        for key, attr in func.__dict__.items():
            if (
                inspect.isfunction(attr)
                or inspect.ismethod(attr)
                or inspect.isclass(attr)
            ):
                if attr.__qualname__.startswith(prefix) and getattr(
                    attr, "__annotations__", None
                ):
                    setattr(
                        func,
                        key,
                        typechecked(attr, always=always, _localns=func.__dict__),
                    )
            elif isinstance(attr, (classmethod, staticmethod)):
                if getattr(attr.__func__, "__annotations__", None):
                    wrapped = typechecked(
                        attr.__func__, always=always, _localns=func.__dict__
                    )
                    setattr(func, key, type(attr)(wrapped))
            elif isinstance(attr, property):
                kwargs = dict(doc=attr.__doc__)
                for name in ("fset", "fget", "fdel"):
                    property_func = kwargs[name] = getattr(attr, name)
                    if property_func is not None and getattr(
                        property_func, "__annotations__", ()
                    ):
                        kwargs[name] = typechecked(
                            property_func, always=always, _localns=func.__dict__
                        )

                setattr(func, key, attr.__class__(**kwargs))

        return func

    if not getattr(func, "__annotations__", None):
        warn(f"no type annotations present -- not typechecking {function_name(func)}")
        return func

    # Find the frame in which the function was declared, for resolving forward
    # references later
    if _localns is None:
        _localns = sys._getframe(1).f_locals

    # Find either the first Python wrapper or the actual function
    python_func = inspect.unwrap(func, stop=lambda f: hasattr(f, "__code__"))

    if not getattr(python_func, "__code__", None):
        warn(f"no code associated -- not typechecking {function_name(func)}")
        return func

    def wrapper(*args, **kwargs):
        if hasattr(wrapper, "__no_type_check__"):
            return func(*args, **kwargs)

        memo = CallMemo(python_func, _localns, args=args, kwargs=kwargs)
        check_argument_types(memo)
        retval = func(*args, **kwargs)
        try:
            check_return_type(retval, memo)
        except TypeError as exc:
            raise TypeError(*exc.args) from None

        # If a generator is returned, wrap it if its yield/send/return types can be
        # checked
        if inspect.isgenerator(retval) or isasyncgen(retval):
            return_type = memo.type_hints.get("return")
            if return_type:
                origin = getattr(return_type, "__origin__", None)
                if origin in generator_origin_types:
                    return TypeCheckedGenerator(retval, memo)
                elif origin is not None and origin in asyncgen_origin_types:
                    return TypeCheckedAsyncGenerator(retval, memo)

        return retval

    async def async_wrapper(*args, **kwargs):
        if hasattr(async_wrapper, "__no_type_check__"):
            return func(*args, **kwargs)

        memo = CallMemo(python_func, _localns, args=args, kwargs=kwargs)
        check_argument_types(memo)
        retval = await func(*args, **kwargs)
        check_return_type(retval, memo)
        return retval

    if inspect.iscoroutinefunction(func):
        if python_func.__code__ is not async_wrapper.__code__:
            return wraps(func)(async_wrapper)
    else:
        if python_func.__code__ is not wrapper.__code__:
            return wraps(func)(wrapper)

    # the target callable was already wrapped
    return func
