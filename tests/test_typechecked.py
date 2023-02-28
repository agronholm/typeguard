from __future__ import annotations

import asyncio
import sys
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Generator,
    Iterable,
    Iterator,
)
from textwrap import dedent
from typing import Any
from unittest.mock import Mock

import pytest

from typeguard import TypeCheckError, suppress_type_checks, typechecked

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class TestCoroutineFunction:
    def test_success(self):
        @typechecked
        async def foo(a: int) -> str:
            return "test"

        assert asyncio.run(foo(1)) == "test"

    def test_bad_arg(self):
        @typechecked
        async def foo(a: int) -> str:
            return "test"

        with pytest.raises(
            TypeCheckError, match=r'argument "a" \(str\) is not an instance of int'
        ):
            asyncio.run(foo("foo"))

    def test_bad_return(self):
        @typechecked
        async def foo(a: int) -> str:
            return 1

        with pytest.raises(
            TypeCheckError, match=r"return value \(int\) is not an instance of str"
        ):
            asyncio.run(foo(1))

    def test_any_return(self):
        @typechecked
        async def foo() -> Any:
            return 1

        assert asyncio.run(foo()) == 1


class TestGenerator:
    def test_generator_bare(self):
        @typechecked
        def genfunc() -> Generator:
            val1 = yield 2
            val2 = yield 3
            val3 = yield 4
            return [val1, val2, val3]

        gen = genfunc()
        with pytest.raises(StopIteration) as exc:
            value = next(gen)
            while True:
                value = gen.send(str(value))
                assert isinstance(value, int)

        assert exc.value.value == ["2", "3", "4"]

    def test_generator_annotated(self):
        @typechecked
        def genfunc() -> Generator[int, str, list[str]]:
            val1 = yield 2
            val2 = yield 3
            val3 = yield 4
            return [val1, val2, val3]

        gen = genfunc()
        with pytest.raises(StopIteration) as exc:
            value = next(gen)
            while True:
                value = gen.send(str(value))
                assert isinstance(value, int)

        assert exc.value.value == ["2", "3", "4"]

    def test_generator_iterable_bare(self):
        @typechecked
        def genfunc() -> Iterable:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_generator_iterable_annotated(self):
        @typechecked
        def genfunc() -> Iterable[int]:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_generator_iterator_bare(self):
        @typechecked
        def genfunc() -> Iterator:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_generator_iterator_annotated(self):
        @typechecked
        def genfunc() -> Iterator[int]:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_bad_yield_as_generator(self):
        @typechecked
        def genfunc() -> Generator[int, str, None]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen)

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_bad_yield_as_iterable(self):
        @typechecked
        def genfunc() -> Iterable[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen)

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_bad_yield_as_iterator(self):
        @typechecked
        def genfunc() -> Iterator[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen)

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_generator_bad_send(self):
        @typechecked
        def genfunc() -> Generator[int, str, None]:
            yield 1
            yield 2

        pass
        gen = genfunc()
        next(gen)
        with pytest.raises(TypeCheckError) as exc:
            gen.send(2)

        exc.match(r"value sent to generator \(int\) is not an instance of str")

    def test_generator_bad_return(self):
        @typechecked
        def genfunc() -> Generator[int, str, str]:
            yield 1
            return 6

        gen = genfunc()
        next(gen)
        with pytest.raises(TypeCheckError) as exc:
            gen.send("foo")

        exc.match(r"return value \(int\) is not an instance of str")

    def test_return_generator(self):
        @typechecked
        def genfunc() -> Generator[int, None, None]:
            yield 1

        @typechecked
        def foo() -> Generator[int, None, None]:
            return genfunc()

        foo()


class TestAsyncGenerator:
    def test_async_generator_bare(self):
        @typechecked
        async def genfunc() -> AsyncGenerator:
            values.append((yield 2))
            values.append((yield 3))
            values.append((yield 4))

        async def run_generator():
            gen = genfunc()
            value = await gen.asend(None)
            with pytest.raises(StopAsyncIteration):
                while True:
                    value = await gen.asend(str(value))
                    assert isinstance(value, int)

        values = []
        asyncio.run(run_generator())
        assert values == ["2", "3", "4"]

    def test_async_generator_annotated(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            values.append((yield 2))
            values.append((yield 3))
            values.append((yield 4))

        async def run_generator():
            gen = genfunc()
            value = await gen.asend(None)
            with pytest.raises(StopAsyncIteration):
                while True:
                    value = await gen.asend(str(value))
                    assert isinstance(value, int)

        values = []
        asyncio.run(run_generator())
        assert values == ["2", "3", "4"]

    def test_generator_iterable_bare(self):
        @typechecked
        async def genfunc() -> AsyncIterable:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_generator_iterable_annotated(self):
        @typechecked
        async def genfunc() -> AsyncIterable[int]:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_generator_iterator_bare(self):
        @typechecked
        async def genfunc() -> AsyncIterator:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_generator_iterator_annotated(self):
        @typechecked
        async def genfunc() -> AsyncIterator[int]:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_async_bad_yield_as_generator(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen.__anext__().__await__())

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_async_bad_yield_as_iterable(self):
        @typechecked
        async def genfunc() -> AsyncIterable[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen.__anext__().__await__())

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_async_bad_yield_as_iterator(self):
        @typechecked
        async def genfunc() -> AsyncIterator[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen.__anext__().__await__())

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_async_generator_bad_send(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            yield 1
            yield 2

        gen = genfunc()
        pytest.raises(StopIteration, next, gen.__anext__().__await__())
        with pytest.raises(TypeCheckError) as exc:
            next(gen.asend(2).__await__())

        exc.match(r"the value sent to generator \(int\) is not an instance of str")

    def test_return_async_generator(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, None]:
            yield 1

        @typechecked
        def foo() -> AsyncGenerator[int, None]:
            return genfunc()

        foo()

    def test_async_generator_iterate(self):
        @typechecked
        async def asyncgenfunc() -> AsyncGenerator[int, None]:
            yield 1

        asyncgen = asyncgenfunc()
        aiterator = asyncgen.__aiter__()
        exc = pytest.raises(StopIteration, aiterator.__anext__().send, None)
        assert exc.value.value == 1


class TestSelf:
    def test_return_valid(self):
        class Foo:
            @typechecked
            def method(self) -> Self:
                return self

        Foo().method

    def test_return_invalid(self):
        class Foo:
            @typechecked
            def method(self) -> Self:
                return 1

        foo = Foo()
        pytest.raises(TypeCheckError, foo.method).match(
            rf"the return value \(int\) is not an instance of the self type "
            rf"\({__name__}\.{self.__class__.__name__}\.test_return_invalid\."
            rf"<locals>\.Foo\)"
        )

    def test_classmethod_return_valid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls) -> Self:
                return Foo()

        Foo.method()

    def test_classmethod_return_invalid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls) -> Self:
                return 1

        pytest.raises(TypeCheckError, Foo.method).match(
            rf"the return value \(int\) is not an instance of the self type "
            rf"\({__name__}\.{self.__class__.__name__}\."
            rf"test_classmethod_return_invalid\.<locals>\.Foo\)"
        )

    def test_arg_valid(self):
        class Foo:
            @typechecked
            def method(self, another: Self) -> None:
                pass

        foo = Foo()
        foo2 = Foo()
        foo.method(foo2)

    def test_arg_invalid(self):
        class Foo:
            @typechecked
            def method(self, another: Self) -> None:
                pass

        foo = Foo()
        pytest.raises(TypeCheckError, foo.method, 1).match(
            rf'argument "another" \(int\) is not an instance of the self type '
            rf"\({__name__}\.{self.__class__.__name__}\.test_arg_invalid\."
            rf"<locals>\.Foo\)"
        )

    def test_classmethod_arg_valid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls, another: Self) -> None:
                pass

        foo = Foo()
        Foo.method(foo)

    def test_classmethod_arg_invalid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls, another: Self) -> None:
                pass

        foo = Foo()
        pytest.raises(TypeCheckError, foo.method, 1).match(
            rf'argument "another" \(int\) is not an instance of the self type '
            rf"\({__name__}\.{self.__class__.__name__}\."
            rf"test_classmethod_arg_invalid\.<locals>\.Foo\)"
        )


class TestMock:
    def test_mock_argument(self):
        @typechecked
        def foo(x: int) -> None:
            pass

        foo(Mock())

    def test_return_mock(self):
        @typechecked
        def foo() -> int:
            return Mock()

        foo()


def test_decorator_before_classmethod():
    class Foo:
        @typechecked
        @classmethod
        def method(cls, x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_classmethod():
    @typechecked
    class Foo:
        @classmethod
        def method(cls, x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_decorator_before_staticmethod():
    class Foo:
        @typechecked
        @staticmethod
        def method(x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_staticmethod():
    @typechecked
    class Foo:
        @staticmethod
        def method(x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_retain_dunder_attributes():
    @typechecked
    def foo(x: int, y: str = "foo") -> None:
        """This is a docstring."""

    assert foo.__module__ == __name__
    assert foo.__name__ == "foo"
    assert foo.__qualname__ == "test_retain_dunder_attributes.<locals>.foo"
    assert foo.__doc__ == "This is a docstring."
    assert foo.__defaults__ == ("foo",)


def test_suppressed_checking():
    @typechecked
    def foo(x: str) -> None:
        pass

    with suppress_type_checks():
        foo(1)


@pytest.mark.skipif(sys.version_info < (3, 9), reason="Requires ast.unparse()")
def test_debug_instrumentation(monkeypatch, capsys):
    monkeypatch.setattr("typeguard.config.debug_instrumentation", True)

    @typechecked
    def foo(a: str) -> int:
        return 6

    out, err = capsys.readouterr()
    assert err == dedent(
        """\
        Source code of test_debug_instrumentation.<locals>.foo() after instrumentation:
        ----------------------------------------------
        def foo(a: str) -> int:
            from typeguard import CallMemo
            from typeguard._functions import check_argument_types, check_return_type
            call_memo = CallMemo(foo, locals())
            check_argument_types(call_memo)
            return check_return_type(6, call_memo)
        ----------------------------------------------
        """
    )


def test_keyword_argument_default():
    # Regression test for #305
    @typechecked
    def foo(*args, x: int | None = None):
        pass

    foo()
