import typing
from typing import Callable

import pytest
from typing_extensions import Literal

from typeguard._union_transformer import compile_type_hint, type_substitutions

eval_globals = {"Callable": Callable, "Literal": Literal, "typing": typing}
eval_globals.update(type_substitutions)


@pytest.mark.parametrize(
    "inputval, expected",
    [
        ["str | int", "Union[str, int]"],
        ["str | int | bytes", "Union[str, int, bytes]"],
        ["str | Union[int | bytes, set]", "Union[str, int, bytes, Set]"],
        ["str | int | Callable[..., bytes]", "Union[str, int, Callable[..., bytes]]"],
        ["str | int | Callable[[], bytes]", "Union[str, int, Callable[[], bytes]]"],
        [
            "str | int | Callable[[], bytes | set]",
            "Union[str, int, Callable[[], Union[bytes, Set]]]",
        ],
        ["str | int | Literal['foo']", "Union[str, int, Literal['foo']]"],
        ["str | int | Literal[-1]", "Union[str, int, Literal[-1]]"],
        ["str | int | Literal[-1]", "Union[str, int, Literal[-1]]"],
        [
            'str | int | Literal["It\'s a string \'\\""]',
            "Union[str, int, Literal['It\\'s a string \\'\"']]",
        ],
        [
            "typing.Tuple | typing.List | Literal[-1]",
            "Union[Tuple, List, Literal[-1]]",
        ],
    ],
)
def test_union_transformer(inputval: str, expected: str) -> None:
    code = compile_type_hint(inputval)
    evaluated = eval(code, eval_globals)
    evaluated_repr = repr(evaluated)
    evaluated_repr = evaluated_repr.replace("typing.", "")
    evaluated_repr = evaluated_repr.replace("typing_extensions.", "")
    assert evaluated_repr == expected
