from __future__ import annotations

import inspect
import sys
from collections.abc import AsyncGenerator, Generator
from inspect import isasyncgenfunction, isclass, isgeneratorfunction
from types import FunctionType
from typing import Any, Dict, ForwardRef, Mapping, Tuple
from weakref import WeakKeyDictionary

from ._config import TypeCheckConfiguration, global_config
from ._utils import function_name

if sys.version_info >= (3, 9):
    from typing import get_type_hints
else:
    from typing_extensions import get_type_hints

from typing_extensions import get_args, get_origin

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
    __slots__ = "func", "func_name", "arguments", "self_type", "type_hints"

    arguments: Mapping[str, Any]
    self: Any
    self_type: type[Any] | None

    def __init__(
        self,
        func: FunctionType,
        frame_locals: dict[str, Any] | None = None,
        args: tuple = None,
        kwargs: dict[str, Any] = None,
        config: TypeCheckConfiguration | None = None,
        *,
        has_self_arg: bool = True,
        unwrap_generator_annotations: bool = False,
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

        # Assume the first argument is bound as "self"
        if has_self_arg and self.arguments:
            first_arg = next(iter(self.arguments.values()))
            self.self_type = first_arg if isclass(first_arg) else type(first_arg)
        else:
            self.self_type = None

        try:
            self.type_hints = _type_hints_map[func]
        except KeyError:
            try:
                self.type_hints = _type_hints_map[func] = get_type_hints(
                    func, localns=frame_locals, include_extras=True
                )
            except NameError:
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
                if origin_type in (Generator, AsyncGenerator):
                    generator_args = get_args(annotation)
                    self.type_hints["yield"] = (
                        generator_args[0] if generator_args else Any
                    )
                    self.type_hints["return"] = (
                        generator_args[2] if len(generator_args) == 3 else Any
                    )

            for key, annotation in list(self.type_hints.items()):
                if key in ("yield", "return"):
                    continue

                param = signature.parameters[key]
                if param.kind is inspect.Parameter.VAR_POSITIONAL:
                    self.type_hints[key] = Tuple[annotation, ...]
                elif param.kind is inspect.Parameter.VAR_KEYWORD:
                    self.type_hints[key] = Dict[str, annotation]
