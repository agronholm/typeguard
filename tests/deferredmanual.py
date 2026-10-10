from __future__ import annotations

from typeguard import check_argument_types


def foo(x: int, /, y: str, *args: bool, z: bytes, **kwargs: int) -> None:
    check_argument_types()
