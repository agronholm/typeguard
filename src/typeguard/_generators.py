import collections.abc
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Generator,
    Iterable,
    Iterator,
)

from ._memo import CallMemo


class TypeCheckedGenerator:
    def __init__(self, wrapped: Generator, memo: CallMemo):
        rtype_args = []
        if hasattr(memo.type_hints["return"], "__args__"):
            rtype_args = memo.type_hints["return"].__args__

        self.__wrapped = wrapped
        self.__memo = memo
        self.__yield_type = rtype_args[0] if rtype_args else Any
        self.__send_type = rtype_args[1] if len(rtype_args) > 1 else Any
        self.__return_type = rtype_args[2] if len(rtype_args) > 2 else Any
        self.__initialized = False

    def __iter__(self):
        return self

    def __next__(self):
        return self.send(None)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped, name)

    def throw(self, *args):
        return self.__wrapped.throw(*args)

    def close(self):
        self.__wrapped.close()

    def send(self, obj):
        from . import check_type

        if self.__initialized:
            check_type(
                obj,
                self.__send_type,
                argname="value sent to generator",
                memo=self.__memo,
            )
        else:
            self.__initialized = True

        try:
            value = self.__wrapped.send(obj)
        except StopIteration as exc:
            check_type(
                exc.value, self.__return_type, argname="return value", memo=self.__memo
            )
            raise

        check_type(
            value,
            self.__yield_type,
            argname="value yielded from generator",
            memo=self.__memo,
        )
        return value


class TypeCheckedAsyncGenerator:
    def __init__(self, wrapped: AsyncGenerator, memo: CallMemo):
        rtype_args = memo.type_hints["return"].__args__
        self.__wrapped = wrapped
        self.__memo = memo
        self.__yield_type = rtype_args[0]
        self.__send_type = rtype_args[1] if len(rtype_args) > 1 else Any
        self.__initialized = False

    def __aiter__(self):
        return self

    def __anext__(self):
        return self.asend(None)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__wrapped, name)

    def athrow(self, *args):
        return self.__wrapped.athrow(*args)

    def aclose(self):
        return self.__wrapped.aclose()

    async def asend(self, obj):
        from . import check_type

        if self.__initialized:
            check_type(
                obj,
                self.__send_type,
                argname="value sent to generator",
                memo=self.__memo,
            )
        else:
            self.__initialized = True

        value = await self.__wrapped.asend(obj)
        check_type(
            value,
            self.__yield_type,
            argname="value yielded from generator",
            memo=self.__memo,
        )
        return value


generator_origin_types = (
    Generator,
    collections.abc.Generator,
    Iterator,
    collections.abc.Iterator,
    Iterable,
    collections.abc.Iterable,
)
asyncgen_origin_types = (
    AsyncIterator,
    collections.abc.AsyncIterator,
    AsyncIterable,
    collections.abc.AsyncIterable,
    AsyncGenerator,
    collections.abc.AsyncGenerator,
)
