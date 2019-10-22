from typing import Literal, TypedDict

import pytest

from typeguard import typechecked


def test_literal():
    @typechecked
    def foo(a: Literal[1, 6, 8]):
        pass

    foo(6)
    pytest.raises(TypeError, foo, 4).match(r'must be one of \(1, 6, 8\); got 4 instead$')


@pytest.mark.parametrize('value, error_re', [
    ({'x': 6, 'y': 'foo'}, None),
    ({'y': 'foo'}, None),
    ({'y': 3}, 'type of dict item "y" for argument "arg" must be str; got int instead'),
    ({}, 'the required key "y" is missing for argument "arg"')
], ids=['correct', 'missing_x', 'wrong_type', 'missing_y'])
def test_typed_dict(value, error_re):
    class DummyDict(TypedDict):
        x: int = 0
        y: str

    @typechecked
    def foo(arg: DummyDict):
        pass

    if error_re:
        pytest.raises(TypeError, foo, value).match(error_re)
    else:
        foo(value)
