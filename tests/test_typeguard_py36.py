from typing import AsyncGenerator

import pytest

from typeguard import TypeChecker, typechecked


class TestTypeChecked:
    def test_async_generator(self):
        async def run_generator():
            @typechecked
            async def genfunc() -> AsyncGenerator[int, str]:
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

    def test_async_generator_bad_yield(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
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


class TestTypeChecker:
    @staticmethod
    async def asyncgenfunc() -> AsyncGenerator[int, None]:
        yield 1

    @pytest.fixture
    def checker(self):
        return TypeChecker(__name__)

    def test_async_generator(self, checker):
        """Make sure that the type checker does not complain about the None return value."""
        with checker, pytest.warns(None) as record:
            self.asyncgenfunc()

        assert len(record) == 0
