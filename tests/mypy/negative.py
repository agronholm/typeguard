from typeguard import check_argument_types, check_return_type, typechecked


@typechecked
def foo(x: int) -> int:
    return x + 1


@typechecked
def bar(x: int) -> int:
    return str(x)  # error: Incompatible return value type (got "str", expected "int")


def arg_type(x: int) -> str:
    return check_argument_types()  # noqa: E501 # error: Incompatible return value type (got "bool", expected "str")


def ret_type() -> str:
    return check_return_type(False)  # noqa: E501 # error: Incompatible return value type (got "bool", expected "str")


_ = arg_type(foo)  # noqa: E501 # error: Argument 1 to "arg_type" has incompatible type "Callable[..., Any]"; expected "int"
