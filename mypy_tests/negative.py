from typeguard import check_argument_types, check_return_type, typechecked


@typechecked
def foo(x: int) -> int:
    return x + 1


def arg_type(x: int) -> str:
    return check_argument_types()  # Error


def ret_type() -> str:
    return check_return_type(False)  # Error


_ = arg_type(foo)  # Error
