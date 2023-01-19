from __future__ import annotations

import inspect
import sys
from functools import partial, wraps
from inspect import isasyncgen, isclass
from typing import TYPE_CHECKING, Any, Callable, TypeVar, overload
from warnings import warn

from . import TypeCheckConfiguration
from ._functions import check_argument_types, check_return_type
from ._generators import (
    TypeCheckedAsyncGenerator,
    TypeCheckedGenerator,
    asyncgen_origin_types,
    generator_origin_types,
)
from ._memo import CallMemo
from ._utils import function_name

if TYPE_CHECKING:
    _F = TypeVar("_F")

    def typeguard_ignore(f: _F) -> _F:
        """This decorator is a noop during static type-checking."""
        return f

else:
    from typing import no_type_check as typeguard_ignore  # noqa: F401

T_CallableOrType = TypeVar("T_CallableOrType", bound=Callable[..., Any])


@overload
def typechecked(
    *, config: TypeCheckConfiguration | None = None
) -> Callable[[T_CallableOrType], T_CallableOrType]:
    ...


@overload
def typechecked(
    func: T_CallableOrType, *, config: TypeCheckConfiguration | None = None
) -> T_CallableOrType:
    ...


def typechecked(
    func: T_CallableOrType | None = None,
    *,
    config: TypeCheckConfiguration | None = None,
    _localns: dict[str, Any] | None = None,
):
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
    :param config:

    """
    if func is None:
        return partial(typechecked, config=config, _localns=_localns)

    if isinstance(func, (classmethod, staticmethod)):
        if isinstance(func, classmethod):
            return classmethod(typechecked(func.__func__))
        else:
            return staticmethod(typechecked(func.__func__))

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
                        typechecked(attr, config=config, _localns=func.__dict__),
                    )
            elif isinstance(attr, (classmethod, staticmethod)):
                if getattr(attr.__func__, "__annotations__", None):
                    wrapped = typechecked(
                        attr.__func__, config=config, _localns=func.__dict__
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
                            property_func, config=config, _localns=func.__dict__
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
