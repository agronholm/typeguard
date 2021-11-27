from __future__ import annotations

import inspect
import sys
from collections import OrderedDict
from inspect import Parameter, isgeneratorfunction
from types import FunctionType
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple
from warnings import warn
from weakref import WeakKeyDictionary

if sys.version_info >= (3, 9):
    from typing import get_type_hints
else:
    from typing_extensions import get_type_hints

if TYPE_CHECKING:
    from .config import TypeCheckConfiguration

_type_hints_map: WeakKeyDictionary[FunctionType, Dict[str, Any]] = WeakKeyDictionary()


def _strip_annotation(annotation):
    if isinstance(annotation, str):
        return annotation.strip("'")
    else:
        return annotation


class TypeCheckMemo:
    __slots__ = 'globals', 'locals', 'config'

    def __init__(self, globals: Dict[str, Any], locals: Dict[str, Any],
                 config: Optional[TypeCheckConfiguration] = None):
        from .config import config as global_config

        self.globals = globals
        self.locals = locals
        self.config = config or global_config


class CallMemo(TypeCheckMemo):
    __slots__ = 'func', 'config', 'func_name', 'arguments', 'is_generator', 'type_hints'

    def __init__(self, func: Callable, frame_locals: Optional[Dict[str, Any]] = None,
                 args: tuple = None, kwargs: Dict[str, Any] = None,
                 config: Optional[TypeCheckConfiguration] = None):
        from .config import ForwardRefPolicy
        from .exceptions import TypeHintWarning
        from .utils import function_name

        super().__init__(func.__globals__, frame_locals, config)
        self.func = func
        self.func_name = function_name(func)
        self.is_generator = isgeneratorfunction(func)
        signature = inspect.signature(func)

        if args is not None and kwargs is not None:
            self.arguments = signature.bind(*args, **kwargs).arguments
        else:
            assert frame_locals is not None, 'frame must be specified if args or kwargs is None'
            self.arguments = frame_locals

        self.type_hints = _type_hints_map.get(func)
        if self.type_hints is None:
            while True:
                try:
                    hints = get_type_hints(func, localns=frame_locals, include_extras=True)
                except NameError as exc:
                    if self.config.forward_ref_policy is ForwardRefPolicy.ERROR:
                        raise

                    typename = str(exc).split("'", 2)[1]
                    for param in signature.parameters.values():
                        if _strip_annotation(param.annotation) == typename:
                            break
                    else:
                        raise

                    func_name = function_name(func)
                    if self.config.forward_ref_policy is ForwardRefPolicy.IGNORE:
                        if param.name in self.arguments:
                            argtype = self.arguments[param.name].__class__
                            stripped = _strip_annotation(param.annotation)
                            if stripped == argtype.__qualname__:
                                func.__annotations__[param.name] = argtype
                                msg = ('Replaced forward declaration {!r} in {} with {!r}'
                                       .format(stripped, func_name, argtype))
                                warn(TypeHintWarning(msg))
                                continue

                    msg = 'Could not resolve type hint {!r} on {}: {}'.format(
                        param.annotation, function_name(func), exc)
                    warn(TypeHintWarning(msg))
                    del func.__annotations__[param.name]
                else:
                    break

            self.type_hints = OrderedDict()
            for name, parameter in signature.parameters.items():
                if name in hints:
                    annotated_type = hints[name]

                    # PEP 428 discourages it by MyPy does not complain
                    if parameter.default is None:
                        annotated_type = Optional[annotated_type]

                    if parameter.kind == Parameter.VAR_POSITIONAL:
                        self.type_hints[name] = Tuple[annotated_type, ...]
                    elif parameter.kind == Parameter.VAR_KEYWORD:
                        self.type_hints[name] = Dict[str, annotated_type]
                    else:
                        self.type_hints[name] = annotated_type

            if 'return' in hints:
                self.type_hints['return'] = hints['return']

            _type_hints_map[func] = self.type_hints
