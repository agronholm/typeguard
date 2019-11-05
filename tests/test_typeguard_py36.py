import warnings
from typing import AsyncGenerator, AsyncIterable, AsyncIterator

import pytest

from typeguard import TypeChecker, typechecked


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
