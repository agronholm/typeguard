import asyncio
import sys
from textwrap import dedent
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Generator,
    Iterable,
    Iterator,
    List,
)
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
            TypeCheckError, match='argument "a" is not an instance of int'
        ):
            asyncio.run(foo("foo"))

    def test_bad_return(self):
        @typechecked
        async def foo(a: int) -> str:
            return 1

        with pytest.raises(
            TypeCheckError, match="return value is not an instance of str"
        ):
            asyncio.run(foo(1))

    def test_any_return(self):
        @typechecked
        async def foo() -> Any:
            return 1

        assert asyncio.run(foo()) == 1


class TestGenerator:
    @pytest.mark.parametrize(
        "annotation",
        [
            pytest.param(Generator[int, str, List[str]], id="generator"),
            pytest.param(Generator, id="bare_generator"),
        ],
    )
    def test_generator(self, annotation):
        @typechecked
        def genfunc() -> annotation:
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

    @pytest.mark.parametrize(
        "annotation",
        [
            pytest.param(Iterable[int], id="iterable"),
            pytest.param(Iterable, id="bare_iterable"),
            pytest.param(Iterator[int], id="iterator"),
            pytest.param(Iterator, id="bare_iterator"),
        ],
    )
    def test_generator_iter_only(self, annotation):
        @typechecked
        def genfunc() -> annotation:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    @pytest.mark.parametrize(
        "annotation",
        [Generator[int, str, None], Iterable[int], Iterator[int]],
        ids=["generator", "iterable", "iterator"],
    )
    def test_generator_bad_yield(self, annotation):
        @typechecked
        def genfunc() -> annotation:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen)

        exc.match("the yielded value is not an instance of int")

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

        exc.match("value sent to generator is not an instance of str")

    def test_generator_bad_return(self):
        @typechecked
        def genfunc() -> Generator[int, str, str]:
            yield 1
            return 6

        gen = genfunc()
        next(gen)
        with pytest.raises(TypeCheckError) as exc:
            gen.send("foo")

        exc.match("return value is not an instance of str")

    def test_return_generator(self):
        @typechecked
        def genfunc() -> Generator[int, None, None]:
            yield 1

        @typechecked
        def foo() -> Generator[int, None, None]:
            return genfunc()

        foo()


class TestAsyncGenerator:
    @pytest.mark.parametrize(
        "annotation",
        [
            pytest.param(AsyncGenerator[int, str], id="generator"),
            pytest.param(AsyncGenerator, id="bare_generator"),
        ],
    )
    def test_async_generator(self, annotation):
        @typechecked
        async def genfunc() -> annotation:
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

    @pytest.mark.parametrize(
        "annotation",
        [
            pytest.param(AsyncIterable[int], id="iterable"),
            pytest.param(AsyncIterable, id="bare_iterable"),
            pytest.param(AsyncIterable[int], id="iterator"),
            pytest.param(AsyncIterable, id="bare_iterator"),
        ],
    )
    def test_generator_iter_only(self, annotation):
        @typechecked
        async def genfunc() -> annotation:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    @pytest.mark.parametrize(
        "annotation",
        [AsyncGenerator[int, str], AsyncIterable[int], AsyncIterator[int]],
        ids=["generator", "iterable", "iterator"],
    )
    def test_async_generator_bad_yield(self, annotation):
        @typechecked
        async def genfunc() -> annotation:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen.__anext__().__await__())

        exc.match("the yielded value is not an instance of int")

    def test_async_generator_bad_send(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            yield 1
            yield 2

        gen = genfunc()
        pytest.raises(StopIteration, next, gen.__anext__().__await__())
        with pytest.raises(TypeCheckError) as exc:
            next(gen.asend(2).__await__())

        exc.match("value sent to generator is not an instance of str")

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
            rf"the return value is not an instance of the self type "
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
            rf"the return value is not an instance of the self type "
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
            rf'argument "another" is not an instance of the self type '
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
            rf'argument "another" is not an instance of the self type '
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
        'argument "x" is not an instance of int'
    )


def test_decorator_before_staticmethod():
    class Foo:
        @typechecked
        @staticmethod
        def method(x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        'argument "x" is not an instance of int'
    )


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
            from typeguard._functions import CallMemo, check_argument_types, \
check_return_type
            call_memo = CallMemo(foo, locals())
            check_argument_types(call_memo)
            return check_return_type(6, call_memo)
        ----------------------------------------------
        """
    )
