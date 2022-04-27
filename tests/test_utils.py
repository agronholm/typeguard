import pytest

from typeguard._utils import function_name, qualified_name

from . import Child


@pytest.mark.parametrize(
    "inputval, expected",
    [(qualified_name, "function"), (Child(), "tests.Child"), (int, "int")],
    ids=["func", "instance", "builtintype"],
)
def test_qualified_name(inputval, expected):
    assert qualified_name(inputval) == expected


def test_function_name():
    assert function_name(function_name) == "typeguard._utils.function_name"
