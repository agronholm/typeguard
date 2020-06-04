import warnings
from typing import AsyncGenerator, AsyncIterable, AsyncIterator

import pytest
from typing_extensions import Literal, Protocol, runtime_checkable

from typeguard import TypeChecker, typechecked


@runtime_checkable
class RuntimeProtocol(Protocol):
    member: int

    def meth(self) -> None:
        ...


class TestTypeChecked:
    @pytest.mark.parametrize('annotation', [
        AsyncGenerator[int, str],
        AsyncIterable[int],
        AsyncIterator[int]
    ], ids=['generator', 'iterable', 'iterator'])
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

        assert values == ['2', '3', '4']

    @pytest.mark.parametrize('annotation', [
        AsyncGenerator[int, str],
        AsyncIterable[int],
        AsyncIterator[int]
    ], ids=['generator', 'iterable', 'iterator'])
    def test_async_generator_bad_yield(self, annotation):
        @typechecked
        async def genfunc() -> annotation:
            yield 'foo'

        gen = genfunc()
        with pytest.raises(TypeError) as exc:
            next(gen.__anext__().__await__())

        exc.match('type of value yielded from generator must be int; got str instead')

    def test_async_generator_bad_send(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            yield 1
            yield 2

        gen = genfunc()
        pytest.raises(StopIteration, next, gen.__anext__().__await__())
        with pytest.raises(TypeError) as exc:
            next(gen.asend(2).__await__())

        exc.match('type of value sent to generator must be str; got int instead')

    def test_return_async_generator(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, None]:
            yield 1

        @typechecked
        def foo() -> AsyncGenerator[int, None]:
            return genfunc()

        foo()


async def asyncgenfunc() -> AsyncGenerator[int, None]:
    yield 1


async def asyncgeniterablefunc() -> AsyncIterable[int]:
    yield 1


async def asyncgeniteratorfunc() -> AsyncIterator[int]:
    yield 1


class TestTypeChecker:
    @pytest.fixture
    def checker(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            return TypeChecker(__name__)

    @pytest.mark.parametrize('func', [asyncgenfunc, asyncgeniterablefunc, asyncgeniteratorfunc],
                             ids=['generator', 'iterable', 'iterator'])
    def test_async_generator(self, checker, func):
        """Make sure that the type checker does not complain about the None return value."""
        with checker, pytest.warns(None) as record:
            func()

        assert len(record) == 0


def test_literal():
    @typechecked
    def foo(a: Literal[1, 6, 8]):
        pass

    foo(6)
    pytest.raises(TypeError, foo, 4).match(r'must be one of \(1, 6, 8\); got 4 instead$')


def test_protocol_non_method_members():
    @typechecked
    def foo(a: RuntimeProtocol):
        pass

    class Foo:
        member = 1

        def meth(self) -> None:
            pass

    foo(Foo())
