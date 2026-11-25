import asyncio
import inspect

import pytest

from typeguard import TypeCheckError, _suppression, check_type, suppress_type_checks


def suppression_level() -> int:
    return _suppression.type_checks_suppressed


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
    # Suppression stays active while the generator is suspended mid-iteration.
    assert suppression_level() == before + 1
    gen.close()
    assert suppression_level() == before


def test_decorator_generator_suppression_ends_after_iteration():
    @suppress_type_checks
    def foo():
        check_type(1, str)
        yield "a"

    list(foo())
    pytest.raises(TypeCheckError, check_type, 1, str)


# Function kind is preserved


def test_decorator_preserves_coroutine_and_generator_kind():
    async def coro() -> None:
        check_type(1, str)

    def gen():
        check_type(1, str)
        yield 1

    assert inspect.iscoroutinefunction(suppress_type_checks(coro))
    assert inspect.isgeneratorfunction(suppress_type_checks(gen))
