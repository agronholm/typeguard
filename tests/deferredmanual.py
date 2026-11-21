from __future__ import annotations

import sys
from typing import NoReturn

if sys.version_info >= (3, 11):
    from typing import Never
else:
    from typing_extensions import Never

from typeguard import check_argument_types


def foo(x: int, /, y: str, *args: bool, z: bytes, **kwargs: int) -> None:
    check_argument_types()


def never_called_noreturn(x: NoReturn) -> None:
    check_argument_types()


def never_called_never(x: Never) -> None:
    check_argument_types()
