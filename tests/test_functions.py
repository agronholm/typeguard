from typeguard import (
    check_argument_types,
    check_return_type,
    check_type,
    suppress_type_checks,
)


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
