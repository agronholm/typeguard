import asyncio
from inspect import iscoroutinefunction

import pytest

from typeguard import TypeCheckError, check_type, suppress_type_checks, typechecked


def test_contextmanager_typechecked():
    @typechecked
    def foo(x: str) -> None:
        pass

    with suppress_type_checks():
        foo(1)


def test_contextmanager_check_type():
    with suppress_type_checks():
        check_type(1, str)


def test_contextmanager_nesting():
    with suppress_type_checks(), suppress_type_checks():
        check_type(1, str)

    pytest.raises(TypeCheckError, check_type, 1, str)


def test_contextmanager_exception():
    """
    Test that type check suppression stops even if an exception is raised within the
    context manager block.

    """
    with pytest.raises(RuntimeError):
        with suppress_type_checks():
            raise RuntimeError

    pytest.raises(TypeCheckError, check_type, 1, str)


@suppress_type_checks
def test_decorator_typechecked():
    @typechecked
    def foo(x: str) -> None:
        pass

    foo(1)


@suppress_type_checks
def test_decorator_check_type():
    check_type(1, str)


def test_decorator_exception():
    """
    Test that type check suppression stops even if an exception is raised from a
    decorated function.

    """

    @suppress_type_checks
    def foo():
        raise RuntimeError

    with pytest.raises(RuntimeError):
        foo()

    pytest.raises(TypeCheckError, check_type, 1, str)


@pytest.mark.parametrize(
    "instrumented", [False, True], ids=["check_type", "typechecked"]
)
def test_decorator_async(instrumented):
    @typechecked
    def checked(value: str) -> None:
        pass

    @suppress_type_checks
    async def target(value, *, result):
        await asyncio.sleep(0)
        if instrumented:
            checked(value)
        else:
            check_type(value, str)

        return result

    assert iscoroutinefunction(target)
    assert target.__name__ == "target"
    coroutine = target(1, result="done")
    try:
        # Creating a coroutine must not start suppression before it runs.
        pytest.raises(TypeCheckError, check_type, 1, str)
        assert asyncio.run(coroutine) == "done"
    finally:
        coroutine.close()

    pytest.raises(TypeCheckError, check_type, 1, str)


def test_decorator_async_nesting():
    @suppress_type_checks
    async def inner():
        await asyncio.sleep(0)
        check_type(1, str)

    @suppress_type_checks
    async def outer():
        await inner()
        check_type(1, str)

    asyncio.run(outer())
    pytest.raises(TypeCheckError, check_type, 1, str)


@pytest.mark.parametrize("cancel", [False, True], ids=["exception", "cancellation"])
def test_decorator_async_exception(cancel):
    @suppress_type_checks
    async def target():
        check_type(1, str)
        if cancel:
            asyncio.current_task().cancel()
            await asyncio.sleep(0)
        else:
            raise RuntimeError

    with pytest.raises(asyncio.CancelledError if cancel else RuntimeError):
        asyncio.run(target())

    pytest.raises(TypeCheckError, check_type, 1, str)
