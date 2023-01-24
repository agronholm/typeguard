"""Module docstring."""
import sys
from contextlib import contextmanager
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Generator,
    Union,
    no_type_check,
    no_type_check_decorator,
    overload,
)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from typeguard import typeguard_ignore


@no_type_check_decorator
def dummy_decorator(func):
    return func


def type_checked_func(x: int, y: int) -> int:
    return x * y


@no_type_check
def non_type_checked_func(x: int, y: str) -> 6:
    return "foo"


@dummy_decorator
def non_type_checked_decorated_func(x: int, y: str) -> 6:
    # This is to ensure that we avoid using a local variable that's already in use
    _call_memo = "foo"  # noqa: F841
    return "foo"


@typeguard_ignore
def non_typeguard_checked_func(x: int, y: str) -> 6:
    return "foo"


def dynamic_type_checking_func(arg, argtype, return_annotation):
    def inner(x: argtype) -> return_annotation:
        return str(x)

    return inner(arg)


class Metaclass(type):
    pass


class DummyClass(metaclass=Metaclass):
    def type_checked_method(self, x: int, y: int) -> int:
        return x * y

    @classmethod
    def type_checked_classmethod(cls, x: int, y: int) -> int:
        return x * y

    @staticmethod
    def type_checked_staticmethod(x: int, y: int) -> int:
        return x * y

    @classmethod
    def undocumented_classmethod(cls, x, y):
        pass

    @staticmethod
    def undocumented_staticmethod(x, y):
        pass

    @property
    def unannotated_property(self):
        return None


def outer():
    class Inner:
        def get_self(self) -> "Inner":
            return self

    def create_inner() -> "Inner":
        return Inner()

    return create_inner


class Outer:
    class Inner:
        pass

    def create_inner(self) -> "Inner":
        return Outer.Inner()

    @classmethod
    def create_inner_classmethod(cls) -> "Inner":
        return Outer.Inner()

    @staticmethod
    def create_inner_staticmethod() -> "Inner":
        return Outer.Inner()


@contextmanager
def dummy_context_manager() -> Generator[int, None, None]:
    yield 1


@overload
def overloaded_func(a: int) -> int:
    ...


@overload
def overloaded_func(a: str) -> str:
    ...


def overloaded_func(a: Union[str, int]) -> Union[str, int]:
    return a


def missing_return() -> int:
    pass


def get_inner_class() -> type:
    class InnerClass:
        def get_self(self) -> "InnerClass":
            return self

    return InnerClass


async def async_func(a: int) -> str:
    return str(a)


def generator_func(yield_value: Any, return_value: Any) -> Generator[int, Any, str]:
    yield yield_value
    return return_value


async def asyncgen_func(yield_value: Any) -> AsyncGenerator[int, Any]:
    yield yield_value


def pep_604_union_args(
    x: "Callable[[], Literal[-1]] | Callable[..., Union[int | str]]",
) -> None:
    pass


def pep_604_union_retval(x: Any) -> "str | int":
    return x
