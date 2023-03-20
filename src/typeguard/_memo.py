from __future__ import annotations

from typing import Any

from typeguard._config import TypeCheckConfiguration, global_config


class TypeCheckMemo:
    __slots__ = "globals", "locals", "self_type", "config"

    def __init__(
        self,
        globals: dict[str, Any],
        locals: dict[str, Any],
        *,
        self_type: type | None = None,
        config: TypeCheckConfiguration = global_config,
    ):
        self.globals = globals
        self.locals = locals
        self.self_type = self_type
        self.config = config
