from typing import Callable
from typeguard import check_argument_types, check_return_type, typechecked


@typechecked
def foo(x: str) -> str:
    return "hello " + x


def takes_callable(f: Callable[[str], str]) -> str:
    return f("typeguard")


_ = takes_callable(foo)


def has_valid_arguments(x: int, y: str) -> bool:
    return check_argument_types()


def has_valid_return_type(y: str) -> str:
    check_return_type(y)
    return y
