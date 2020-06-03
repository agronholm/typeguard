from __future__ import annotations

from typing import Literal, TypedDict, Union

import pytest

from typeguard import typechecked


def test_literal():
    @typechecked
    def foo(a: Literal[1, 6, 8]):
        pass

    foo(6)
    pytest.raises(TypeError, foo, 4).match(r'must be one of \(1, 6, 8\); got 4 instead$')


def test_literal_union():
    @typechecked
    def foo(a: Union[str, Literal[1, 6, 8]]):
        pass

    foo(6)
    pytest.raises(TypeError, foo, 4).\
        match(r'must be one of \(str, typing.Literal\[1, 6, 8\]\); got int instead$')


@pytest.mark.parametrize('value, total, error_re', [
    ({'x': 6, 'y': 'foo'}, True, None),
    ({'y': 'foo'}, True, r'required key\(s\) \("x"\) missing from argument "arg"'),
    ({'x': 6, 'y': 3}, True,
     'type of dict item "y" for argument "arg" must be str; got int instead'),
    ({'x': 6}, True, r'required key\(s\) \("y"\) missing from argument "arg"'),
    ({'x': 6}, False, None),
    ({'x': 'abc'}, False, 'type of dict item "x" for argument "arg" must be int; got str instead'),
    ({'x': 6, 'foo': 'abc'}, False, r'extra key\(s\) \("foo"\) in argument "arg"'),
], ids=['correct', 'missing_x', 'wrong_y', 'missing_y_error', 'missing_y_ok', 'wrong_x',
        'unknown_key'])
def test_typed_dict(value, total, error_re):
    class DummyDict(TypedDict, total=total):
        x: int
        y: str

    @typechecked
    def foo(arg: DummyDict):
        pass

    if error_re:
        pytest.raises(TypeError, foo, value).match(error_re)
    else:
        foo(value)
