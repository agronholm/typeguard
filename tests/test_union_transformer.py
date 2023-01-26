import pytest

from typeguard._union_transformer import translate_type_hint


@pytest.mark.parametrize(
    "inputval, expected",
    [
        ["a | b", "Union[a, b]"],
        ["a | b | c", "Union[a, b, c]"],
        ["a | Union[b | c, d]", "Union[a, Union[Union[b, c], d]]"],
        ["a | b | Callable[..., c]", "Union[a, b, Callable[..., c]]"],
        ["a | b | Callable[[], c]", "Union[a, b, Callable[[], c]]"],
        ["a | b | Callable[[], c | d]", "Union[a, b, Callable[[], Union[c, d]]]"],
        ["a | b | Literal[1]", "Union[a, b, Literal[1]]"],
        ["a | b | Literal[-1]", "Union[a, b, Literal[-1]]"],
        ["a | b | Literal[-1]", "Union[a, b, Literal[-1]]"],
        [
            'a | b | Literal["It\'s a string \'\\""]',
            'Union[a, b, Literal["It\'s a string \'\\""]]',
        ],
        [
            "typing.Tuple | typing.List | Literal[-1]",
            "Union[typing.Tuple, typing.List, Literal[-1]]"
        ],
    ],
)
def test_union_transformer(inputval, expected):
    assert translate_type_hint(inputval) == expected
