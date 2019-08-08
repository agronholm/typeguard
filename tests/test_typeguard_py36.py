from typing import AsyncGenerator

import pytest

from typeguard import TypeChecker


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
