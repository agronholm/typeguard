import sys
from collections.abc import Sequence
from typing import NoReturn, Union

import pytest

from typeguard import TypeCheckError, check_type

if sys.version_info >= (3, 11):
    from typing import Never
else:
    from typing_extensions import Never


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        pytest.param(list[Never], [1], id="list"),
        pytest.param(dict[str, Never], {"key": 1}, id="dict"),
        pytest.param(Union[int, Never], "value", id="union"),
        pytest.param(Union[Never, None], 1, id="optional"),
        pytest.param(tuple[Never, ...], (1, 2), id="tuple"),
        pytest.param(Sequence[NoReturn], [1], id="sequence-noreturn"),
    ],
)
def test_nested_never_rejects_values(annotation, value):
    with pytest.raises(TypeCheckError):
        check_type(value, annotation)


def test_union_with_never_accepts_other_member():
    assert check_type(1, Union[int, Never]) == 1
