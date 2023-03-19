from __future__ import annotations

from typing import Any


class TypeCheckMemo:
    __slots__ = "globals", "locals", "self_type"

    def __init__(
        self,
        globals: dict[str, Any],
        locals: dict[str, Any],
        self_type: type | None = None,
    ):
        self.globals = globals
        self.locals = locals
        self.self_type = self_type
