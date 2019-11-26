from typing import Literal, TypedDict

import pytest

from typeguard import typechecked


def test_literal():
    @typechecked
    def foo(a: Literal[1, 6, 8]):
        pass

    foo(6)
    pytest.raises(TypeError, foo, 4).match(r'must be one of \(1, 6, 8\); got 4 instead$')


@pytest.mark.parametrize('value, total, error_re', [
    ({'x': 6, 'y': 'foo'}, True, None),
    ({'y': 'foo'}, True, None),
    ({'y': 3}, True, 'type of dict item "y" for argument "arg" must be str; got int instead'),
    ({}, True, 'the required key "y" is missing for argument "arg"'),
    ({}, False, None),
    ({'x': 'abc'}, False, 'type of dict item "x" for argument "arg" must be int; got str instead')
], ids=['correct', 'missing_x', 'wrong_y', 'missing_y', 'empty_dict', 'wrong_x'])
def test_typed_dict(value, total, error_re):
    class DummyDict(TypedDict, total=total):
        x: int = 0
        y: str

    @typechecked
    def foo(arg: DummyDict):
        pass

    if error_re:
        pytest.raises(TypeError, foo, value).match(error_re)
    else:
        foo(value)
