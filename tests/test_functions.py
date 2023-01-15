import sys
from typing import NoReturn

import pytest

from typeguard import (
    TypeCheckError,
    check_argument_types,
    check_return_type,
    check_type,
    suppress_type_checks,
    typechecked,
)

if sys.version_info >= (3, 11):
    from typing import Never
else:
    from typing_extensions import Never


def test_check_type_suppressed():
    with suppress_type_checks():
        check_type(1, str)


def test_check_argument_types_suppressed():
    def foo(x: int):
        check_argument_types()

    with suppress_type_checks():
        foo("x")


def test_check_return_value_suppressed():
    def foo() -> int:
        check_return_type("x")

    with suppress_type_checks():
        foo()


@pytest.mark.parametrize("annotation", [NoReturn, Never])
def test_check_never_in_args(annotation):
    @typechecked
    def foo(x: annotation) -> None:
        pass

    pytest.raises(TypeCheckError, foo, 1).match(
        r"foo\(\) was declared never to be called but it was"
    )


@pytest.mark.parametrize("annotation", [NoReturn, Never])
def test_check_never_in_retval(annotation):
    @typechecked
    def foo() -> annotation:
        pass

    pytest.raises(TypeCheckError, foo).match(
        r"foo\(\) was declared never to return but it did"
    )
