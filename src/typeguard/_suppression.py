from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import update_wrapper
from inspect import isasyncgenfunction, iscoroutinefunction, isgeneratorfunction
from typing import Any, Awaitable, ContextManager, ParamSpec, TypeVar, cast, overload

P = ParamSpec("P")
T = TypeVar("T")

# Suppression is context-local: asyncio tasks run in separate contexts, so a
# module-global counter would suppress checks in unrelated concurrent tasks.
type_checks_suppressed: ContextVar[int] = ContextVar(
    "type_checks_suppressed", default=0
)


def is_suppressed() -> bool:
    """Return whether type checks are suppressed in the current context."""
    return type_checks_suppressed.get() > 0


@contextmanager
def _suppression() -> Generator[None, None, None]:
    """Activate suppression for the duration of this context, then restore it."""
    token = type_checks_suppressed.set(type_checks_suppressed.get() + 1)
    try:
        yield
    finally:
        type_checks_suppressed.reset(token)


@overload
def suppress_type_checks(func: Callable[P, T]) -> Callable[P, T]: ...


@overload
def suppress_type_checks() -> ContextManager[None]: ...


def suppress_type_checks(
    func: Callable[P, T] | None = None,
) -> Callable[P, T] | ContextManager[None]:
    """
    Temporarily suppress all type checking.

    This function has two operating modes, based on how it's used:

    #. as a context manager (``with suppress_type_checks(): ...``)
    #. as a decorator (``@suppress_type_checks``)

    When used as a context manager, :func:`check_type` and any automatically
    instrumented functions skip the actual type checking. These context managers can be
    nested.

    When used as a decorator, all type checking is suppressed while the function is
    running.

    Type checking will resume once no more context managers are active and no decorated
    functions are running.

    Suppression is local to the current context, so concurrent asyncio tasks do not
    suppress checks in one another. Generators and coroutines only suppress their own
    body: a generator does not suppress type checks in its caller while suspended.

    """

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        assert func is not None
        with _suppression():
            return func(*args, **kwargs)

    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        assert func is not None
        with _suppression():
            return await cast(Awaitable[Any], func(*args, **kwargs))

    def generator_wrapper(
        *args: P.args, **kwargs: P.kwargs
    ) -> Generator[Any, Any, Any]:
        assert func is not None
        gen = cast(Generator[Any, Any, Any], func(*args, **kwargs))

        class SteppedGenerator:
            """Delegate the generator protocol, suppressing only each step."""

            def __iter__(self) -> SteppedGenerator:
                return self

            def __next__(self) -> Any:
                with _suppression():
                    return next(gen)

            def send(self, value: Any) -> Any:
                with _suppression():
                    return gen.send(value)

            def throw(self, *exc: Any) -> Any:
                with _suppression():
                    return gen.throw(*exc)

            def close(self) -> None:
                with _suppression():
                    gen.close()

        # yield from forwards throw() and close(), and returning its result
        # preserves StopIteration.value from the wrapped generator.
        return (yield from SteppedGenerator())

    async def async_generator_wrapper(
        *args: P.args, **kwargs: P.kwargs
    ) -> AsyncGenerator[Any, Any]:
        assert func is not None
        gen = cast(AsyncGenerator[Any, Any], func(*args, **kwargs))
        sent: Any = None
        try:
            while True:
                # asend(None) is equivalent to __anext__() for a fresh generator.
                with _suppression():
                    try:
                        value = await gen.asend(sent)
                    except StopAsyncIteration:
                        return
                sent = yield value
        finally:
            await gen.aclose()

    if func is None:
        # Context manager mode
        return _suppression()
    elif iscoroutinefunction(func):
        # Decorator mode, coroutine function
        update_wrapper(async_wrapper, func)
        return cast(Callable[P, T], async_wrapper)
    elif isasyncgenfunction(func):
        # Decorator mode, async generator function
        update_wrapper(async_generator_wrapper, func)
        return cast(Callable[P, T], async_generator_wrapper)
    elif isgeneratorfunction(func):
        # Decorator mode, generator function
        update_wrapper(generator_wrapper, func)
        return cast(Callable[P, T], generator_wrapper)
    else:
        # Decorator mode
        update_wrapper(wrapper, func)
        return wrapper
