from __future__ import annotations

import gc
import inspect
import sys
from types import CodeType, FunctionType
from typing import Any, Callable, Dict, Optional, Tuple, get_type_hints
from weakref import WeakValueDictionary

from .memo import TypeCheckMemo

if sys.version_info >= (3, 9):
    from typing import Annotated, get_args, get_origin
else:
    from typing_extensions import Annotated, get_args, get_origin

_functions_map: WeakValueDictionary[CodeType, FunctionType] = WeakValueDictionary()


def get_type_hints_with_extra(
    annotation: Any, memo: TypeCheckMemo
) -> Dict[str, Tuple[Any, Tuple]]:
    type_hints: Dict[str, Tuple[Any, Tuple]] = {}
    result = get_type_hints(annotation, memo.globals, memo.locals)
    for key, value in result.items():
        origin = get_origin(value)
        if origin is Annotated:
            type_hints[key] = value.__args__[0], value.__metadata__
        else:
            type_hints[key] = value, ()

    return type_hints


def get_type_name(type_) -> str:
    name = (getattr(type_, '__name__', None) or getattr(type_, '_name', None) or
            getattr(type_, '__forward_arg__', None))
    if name is None:
        origin = get_origin(type_)
        name = getattr(origin, '_name', None)
        if name is None and not inspect.isclass(type_):
            name = type_.__class__.__name__.strip('_')

    args = get_args(type_)
    if args:
        if name == 'Literal':
            formatted_args = ', '.join(str(arg) for arg in args)
        else:
            formatted_args = ', '.join(get_type_name(arg) for arg in args)

        name += f'[{formatted_args}]'

    module = getattr(type_, '__module__', None)
    if module not in (None, 'typing', 'typing_extensions', 'builtins'):
        name = module + '.' + name

    return name


def find_function(frame) -> Optional[Callable]:
    """
    Return a function object from the garbage collector that matches the frame's code object.

    This process is unreliable as several function objects could use the same code object.
    Fortunately the likelihood of this happening with the combination of the function objects
    having different type annotations is a very rare occurrence.

    :param frame: a frame object
    :return: a function object if one was found, ``None`` if not

    """
    func = _functions_map.get(frame.f_code)
    if func is None:
        for obj in gc.get_referrers(frame.f_code):
            if inspect.isfunction(obj):
                if func is None:
                    # The first match was found
                    func = obj
                else:
                    # A second match was found
                    return None

        # Cache the result for future lookups
        if func is not None:
            _functions_map[frame.f_code] = func
        else:
            raise LookupError('target function not found')

    return func


def qualified_name(obj: Any) -> str:
    """
    Return the qualified name (e.g. package.module.Type) for the given object.

    Builtins and types from the :mod:`typing` package get special treatment by having the module
    name stripped from the generated name.

    """
    type_ = obj if inspect.isclass(obj) else type(obj)
    module = type_.__module__
    qualname = type_.__qualname__
    return qualname if module in ('typing', 'builtins') else f'{module}.{qualname}'


def function_name(func: Callable) -> str:
    """
    Return the qualified name of the given function.

    Builtins and types from the :mod:`typing` package get special treatment by having the module
    name stripped from the generated name.

    """
    # For partial functions and objects with __call__ defined, __qualname__ does not exist
    module = getattr(func, '__module__', '')
    qualname = (module + '.') if module not in ('builtins', '') else ''
    return qualname + getattr(func, '__qualname__', repr(func))
