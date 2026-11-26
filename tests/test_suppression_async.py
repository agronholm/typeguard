import asyncio
import inspect

import pytest

from typeguard import TypeCheckError, _suppression, check_type, suppress_type_checks


def suppression_level() -> int:
    return _suppression.type_checks_suppressed.get()


# Coroutine bodies


def test_decorator_coroutine_body_suppresses():
    @suppress_type_checks
    async def foo() -> None:
        check_type(1, str)

    before = suppression_level()
    asyncio.run(foo())
    assert suppression_level() == before


def test_decorator_coroutine_counter_restored_on_exception():
    @suppress_type_checks
    async def foo() -> None:
        check_type(1, str)
        raise RuntimeError("boom")

    before = suppression_level()
    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(foo())
    assert suppression_level() == before


def test_decorator_coroutine_counter_restored_on_cancellation():
    started = asyncio.Event()

    @suppress_type_checks
    async def foo() -> None:
        started.set()
        check_type(1, str)
        await asyncio.Event().wait()  # cancelled here

    async def run() -> None:
        task = asyncio.create_task(foo())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    before = suppression_level()
    asyncio.run(run())
    assert suppression_level() == before


def test_decorator_coroutine_suppression_ends_after_completion():
    @suppress_type_checks
    async def foo() -> None:
        check_type(1, str)

    asyncio.run(foo())
    pytest.raises(TypeCheckError, check_type, 1, str)


def test_coroutine_suppression_does_not_leak_to_unrelated_task():
    entered = asyncio.Event()
    release = asyncio.Event()

    @suppress_type_checks
    async def decorated() -> None:
        check_type(1, str)  # suppressed inside the decorated coroutine
        entered.set()
        await release.wait()

    async def unrelated() -> None:
        await entered.wait()
        # Suppression in `decorated` is local to its task, not global.
        with pytest.raises(TypeCheckError):
            check_type(1, str)

    async def run() -> None:
        task_a = asyncio.create_task(decorated())
        task_b = asyncio.create_task(unrelated())
        await entered.wait()
        release.set()
        await task_a
        await task_b

    asyncio.run(run())


# Generator bodies


def test_decorator_generator_body_suppresses():
    @suppress_type_checks
    def foo():
        check_type(1, str)
        yield "a"
        check_type(1, str)
        yield "b"

    before = suppression_level()
    assert list(foo()) == ["a", "b"]
    assert suppression_level() == before


def test_decorator_generator_counter_restored_on_exception():
    @suppress_type_checks
    def foo():
        check_type(1, str)
        yield "a"
        raise RuntimeError("boom")

    before = suppression_level()
    gen = foo()
    assert next(gen) == "a"
    with pytest.raises(RuntimeError, match="boom"):
        next(gen)
    assert suppression_level() == before


def test_decorator_generator_counter_restored_on_close():
    @suppress_type_checks
    def foo():
        check_type(1, str)
        yield "a"
        check_type(1, str)
        yield "b"

    before = suppression_level()
    gen = foo()
    assert next(gen) == "a"
    # Suppression is scoped to each step, so it is inactive while suspended.
    assert suppression_level() == before
    gen.close()
    assert suppression_level() == before


def test_decorator_generator_suppression_ends_after_iteration():
    @suppress_type_checks
    def foo():
        check_type(1, str)
        yield "a"

    list(foo())
    pytest.raises(TypeCheckError, check_type, 1, str)


def test_decorator_generator_preserves_stop_iteration_value():
    @suppress_type_checks
    def foo():
        yield "a"
        return 42

    gen = foo()
    assert next(gen) == "a"
    with pytest.raises(StopIteration) as exc_info:
        next(gen)
    assert exc_info.value.value == 42


def test_caller_check_not_suppressed_while_generator_is_suspended():
    @suppress_type_checks
    def foo():
        check_type(1, str)  # suppressed inside the generator body
        yield "a"
        check_type(1, str)

    gen = foo()
    assert next(gen) == "a"
    # The generator is suspended at `yield "a"`; its suppression must not
    # remain active in the caller's context.
    with pytest.raises(TypeCheckError):
        check_type(1, str)
    assert list(gen) == []
    pytest.raises(TypeCheckError, check_type, 1, str)


# Async generator bodies


def test_decorator_async_generator_body_suppresses():
    @suppress_type_checks
    async def foo():
        check_type(1, str)
        yield "a"
        check_type(1, str)
        yield "b"

    async def run() -> None:
        assert [item async for item in foo()] == ["a", "b"]

    before = suppression_level()
    asyncio.run(run())
    assert suppression_level() == before
    pytest.raises(TypeCheckError, check_type, 1, str)


# Function kind is preserved


def test_decorator_preserves_coroutine_and_generator_kind():
    async def coro() -> None:
        check_type(1, str)

    def gen():
        check_type(1, str)
        yield 1

    async def agen():
        check_type(1, str)
        yield 1

    assert inspect.iscoroutinefunction(suppress_type_checks(coro))
    assert inspect.isgeneratorfunction(suppress_type_checks(gen))
    assert inspect.isasyncgenfunction(suppress_type_checks(agen))
