import asyncio
import sys
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

import pytest

from typeguard import TypeCheckError, typechecked

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
            Generator[int, str, List[str]],
            Generator,
            Iterable[int],
            Iterable,
            Iterator[int],
            Iterator,
        ],
        ids=[
            "generator",
            "bare_generator",
            "iterable",
            "bare_iterable",
            "iterator",
            "bare_iterator",
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

        exc.match("value yielded from generator is not an instance of int")

    def test_generator_bad_send(self):
        @typechecked
        def genfunc() -> Generator[int, str, None]:
            yield 1
            yield 2

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
        [AsyncGenerator[int, str], AsyncIterable[int], AsyncIterator[int]],
        ids=["generator", "iterable", "iterator"],
    )
    def test_async_generator(self, annotation):
        async def run_generator():
            @typechecked
            async def genfunc() -> annotation:
                values.append((yield 2))
                values.append((yield 3))
                values.append((yield 4))

            gen = genfunc()

            value = await gen.asend(None)
            with pytest.raises(StopAsyncIteration):
                while True:
                    value = await gen.asend(str(value))
                    assert isinstance(value, int)

        values = []
        coro = run_generator()
        try:
            for elem in coro.__await__():
                print(elem)
        except StopAsyncIteration as exc:
            values = exc.value

        assert values == ["2", "3", "4"]

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

        exc.match("value yielded from generator is not an instance of int")

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
