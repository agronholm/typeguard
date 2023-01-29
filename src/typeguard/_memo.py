from __future__ import annotations

import inspect
import sys
from collections.abc import (
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Generator,
    Iterable,
    Iterator,
)
from inspect import isasyncgenfunction, isclass, isgeneratorfunction
from types import FunctionType
from typing import Any, Dict, ForwardRef, Tuple
from weakref import WeakKeyDictionary

from ._config import TypeCheckConfiguration, global_config
from ._utils import function_name

if sys.version_info >= (3, 11):
    from typing import get_args, get_origin
else:
    from typing_extensions import get_args, get_origin

if sys.version_info >= (3, 9):
    from typing import get_type_hints
else:
    from typing_extensions import get_type_hints

_type_hints_map: WeakKeyDictionary[
    FunctionType, tuple[dict[str, Any], Any, Any]
] = WeakKeyDictionary()


class TypeCheckMemo:
    __slots__ = "globals", "locals", "config"

    def __init__(
        self,
        globals: dict[str, Any],
        locals: dict[str, Any],
        config: TypeCheckConfiguration | None = None,
    ):
        self.globals = globals
        self.locals = locals
        self.config = config or global_config


class CallMemo(TypeCheckMemo):
    __slots__ = "func", "arguments", "self_type", "type_hints"

    arguments: dict[str, Any]
    self_type: type[Any] | None

    def __init__(
        self,
        func: FunctionType,
        frame_locals: dict[str, Any] | None = None,
        config: TypeCheckConfiguration | None = None,
        *,
        has_self_arg: bool = True,
        unwrap_generator_annotations: bool = False,
    ):
        super().__init__(func.__globals__, frame_locals, config)
        self.func = func

        assert (
            frame_locals is not None
        ), "frame must be specified if args or kwargs is None"
        self.arguments = frame_locals.copy()
        self.arguments.pop("typeguard", None)

        # Assume the first argument is bound as "self"
        if has_self_arg and self.arguments:
            first_arg = next(iter(self.arguments.values()))
            self.self_type = first_arg if isclass(first_arg) else type(first_arg)
        else:
            self.self_type = None

        func = inspect.unwrap(func)
        try:
            self.type_hints = _type_hints_map[func]
        except KeyError:
            try:
                self.type_hints = _type_hints_map[func] = get_type_hints(
                    func, localns=frame_locals, include_extras=True
                )
            except (TypeError, NameError):
                type_hints = {}
                for key, annotation in func.__annotations__.items():
                    if type(annotation) is str:
                        annotation = ForwardRef(annotation)

                    type_hints[key] = annotation

                self.type_hints = type_hints

            if (
                unwrap_generator_annotations
                and "return" in self.type_hints
                and (isgeneratorfunction(func) or isasyncgenfunction(func))
            ):
                annotation = self.type_hints["return"]
                origin_type = get_origin(annotation)
                annotation_args = get_args(annotation)
                if isgeneratorfunction(func):
                    if origin_type is Generator:
                        self.type_hints["yield"] = (
                            annotation_args[0] if annotation_args else Any
                        )
                        self.type_hints[":send"] = (
                            annotation_args[1] if annotation_args else Any
                        )
                        self.type_hints["return"] = (
                            annotation_args[2] if annotation_args else Any
                        )
                    elif origin_type is Iterator or origin_type is Iterable:
                        self.type_hints["yield"] = (
                            annotation_args[0] if annotation_args else Any
                        )
                        self.type_hints[":send"] = type(None)
                        del self.type_hints["return"]
                elif isasyncgenfunction(func):
                    if origin_type is AsyncGenerator:
                        self.type_hints["yield"] = (
                            annotation_args[0] if annotation_args else Any
                        )
                        self.type_hints[":send"] = (
                            annotation_args[1] if annotation_args else Any
                        )
                        del self.type_hints["return"]
                    elif origin_type is AsyncIterator or origin_type is AsyncIterable:
                        self.type_hints["yield"] = (
                            annotation_args[0] if annotation_args else Any
                        )
                        self.type_hints[":send"] = type(None)
                        del self.type_hints["return"]

            signature = inspect.signature(func)
            for key, annotation in list(self.type_hints.items()):
                if key in ("yield", "return", ":send"):
                    continue

                param = signature.parameters[key]
                if param.kind is inspect.Parameter.VAR_POSITIONAL:
                    self.type_hints[key] = Tuple[annotation, ...]
                elif param.kind is inspect.Parameter.VAR_KEYWORD:
                    self.type_hints[key] = Dict[str, annotation]

    @property
    def func_name(self) -> str:
        return function_name(self.func)
