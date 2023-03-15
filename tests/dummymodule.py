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

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from typeguard import typechecked, typeguard_ignore

P = ParamSpec("P")


@no_type_check_decorator
def dummy_decorator(func):
    return func


@typechecked
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
    @typechecked
    def inner(x: argtype) -> return_annotation:
        return str(x)

    return inner(arg)


class Metaclass(type):
    pass


@typechecked
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
    @typechecked
    class Inner:
        def get_self(self) -> "Inner":
            return self

    def create_inner() -> "Inner":
        return Inner()

    return create_inner


@typechecked
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
@typechecked
def dummy_context_manager() -> Generator[int, None, None]:
    yield 1


@overload
def overloaded_func(a: int) -> int:
    ...


@overload
def overloaded_func(a: str) -> str:
    ...


@typechecked
def overloaded_func(a: Union[str, int]) -> Union[str, int]:
    return a


@typechecked
def missing_return() -> int:
    pass


def get_inner_class() -> type:
    @typechecked
    class InnerClass:
        def get_self(self) -> "InnerClass":
            return self

    return InnerClass


@typechecked
async def async_func(a: int) -> str:
    return str(a)


@typechecked
def generator_func(yield_value: Any, return_value: Any) -> Generator[int, Any, str]:
    yield yield_value
    return return_value


@typechecked
async def asyncgen_func(yield_value: Any) -> AsyncGenerator[int, Any]:
    yield yield_value


@typechecked
def pep_604_union_args(
    x: "Callable[[], Literal[-1]] | Callable[..., Union[int | str]]",
) -> None:
    pass


@typechecked
def pep_604_union_retval(x: Any) -> "str | int":
    return x


@typechecked
def paramspec_function(func: P, args: P.args, kwargs: P.kwargs) -> None:
    pass


@typechecked
def aug_assign() -> int:
    x: int = 1
    x += 1
    return x


@typechecked
def unpacking_assign() -> "tuple[int, str]":
    x: int
    y: str
    x, y = (1, "foo")
    return x, y
