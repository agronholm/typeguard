from __future__ import annotations

import inspect
import sys
from types import FunctionType
from typing import TYPE_CHECKING, Any, Mapping
from weakref import WeakKeyDictionary

from ._utils import function_name

if sys.version_info >= (3, 9):
    from typing import get_type_hints
else:
    from typing_extensions import get_type_hints

if TYPE_CHECKING:
    from ._config import TypeCheckConfiguration

_type_hints_map: WeakKeyDictionary[FunctionType, dict[str, Any]] = WeakKeyDictionary()


class TypeCheckMemo:
    __slots__ = "globals", "locals", "config"

    def __init__(
        self,
        globals: dict[str, Any],
        locals: dict[str, Any],
        config: TypeCheckConfiguration | None = None,
    ):
        from . import config as global_config

        self.globals = globals
        self.locals = locals
        self.config = config or global_config


class CallMemo(TypeCheckMemo):
    __slots__ = "func", "func_name", "arguments", "type_hints"

    arguments: Mapping[str, Any]

    def __init__(
        self,
        func: FunctionType,
        frame_locals: dict[str, Any] | None = None,
        args: tuple = None,
        kwargs: dict[str, Any] = None,
        config: TypeCheckConfiguration | None = None,
    ):
        super().__init__(func.__globals__, frame_locals, config)
        self.func = func
        self.func_name = function_name(func)
        signature = inspect.signature(func)

        if args is not None and kwargs is not None:
            self.arguments = signature.bind(*args, **kwargs).arguments
        else:
            assert (
                frame_locals is not None
            ), "frame must be specified if args or kwargs is None"
            self.arguments = frame_locals

        try:
            self.type_hints = _type_hints_map[func]
        except KeyError:
            self.type_hints = _type_hints_map[func] = get_type_hints(
                func, localns=frame_locals, include_extras=True
            )
