from __future__ import annotations

import gc
import inspect
import sys
from types import CodeType, FrameType, FunctionType
from typing import TYPE_CHECKING, Any, Callable, ForwardRef
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    from ._memo import TypeCheckMemo

try:
    from typing_extensions import is_typeddict
except ImportError:
    if sys.version_info >= (3, 10):
        from typing import is_typeddict
    else:
        _typed_dict_meta_types = ()
        if sys.version_info >= (3, 8):
            from typing import _TypedDictMeta

            _typed_dict_meta_types += (_TypedDictMeta,)

        try:
            from typing_extensions import _TypedDictMeta

            _typed_dict_meta_types += (_TypedDictMeta,)
        except ImportError:
            pass

        def is_typeddict(tp) -> bool:
            return isinstance(tp, _typed_dict_meta_types)


if sys.version_info >= (3, 9):
    from typing import get_args, get_origin

    def evaluate_forwardref(forwardref: ForwardRef, memo: TypeCheckMemo) -> Any:
        return forwardref._evaluate(memo.globals, memo.locals, frozenset())

else:
    from typing_extensions import get_args, get_origin

    def evaluate_forwardref(forwardref: ForwardRef, memo: TypeCheckMemo) -> Any:
        return forwardref._evaluate(memo.globals, memo.locals)


_functions_map: WeakValueDictionary[CodeType, FunctionType] = WeakValueDictionary()


def get_type_name(type_) -> str:
    name = (
        getattr(type_, "__name__", None)
        or getattr(type_, "_name", None)
        or getattr(type_, "__forward_arg__", None)
    )
    if name is None:
        origin = get_origin(type_)
        name = getattr(origin, "_name", None)
        if name is None and not inspect.isclass(type_):
            name = type_.__class__.__name__.strip("_")

    args = get_args(type_)
    if args:
        if name == "Literal":
            formatted_args = ", ".join(str(arg) for arg in args)
        else:
            formatted_args = ", ".join(get_type_name(arg) for arg in args)

        name += f"[{formatted_args}]"

    module = getattr(type_, "__module__", None)
    if module not in (None, "typing", "typing_extensions", "builtins"):
        name = module + "." + name

    return name


def find_function(frame: FrameType) -> Callable:
    """
    Return a function object from the garbage collector that matches the frame's code
    object.

    This process is unreliable as several function objects could use the same code
    object. Fortunately the likelihood of this happening with the combination of the
    function objects having different type annotations is a very rare occurrence.

    :param frame: a frame object
    :return: a function object
    :raises LookupError: if not exactly one matching function object was found

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
                    raise LookupError(
                        f"two functions matched: {qualified_name(func)} and "
                        f"{qualified_name(obj)}"
                    )

        # Cache the result for future lookups
        if func is not None:
            _functions_map[frame.f_code] = func
        else:
            raise LookupError("target function not found")

    return func


def qualified_name(obj: Any) -> str:
    """
    Return the qualified name (e.g. package.module.Type) for the given object.

    Builtins and types from the :mod:`typing` package get special treatment by having
    the module name stripped from the generated name.

    """
    type_ = obj if inspect.isclass(obj) else type(obj)
    module = type_.__module__
    qualname = type_.__qualname__
    return qualname if module in ("typing", "builtins") else f"{module}.{qualname}"


def function_name(func: Callable) -> str:
    """
    Return the qualified name of the given function.

    Builtins and types from the :mod:`typing` package get special treatment by having
    the module name stripped from the generated name.

    """
    # For partial functions and objects with __call__ defined, __qualname__ does not
    # exist
    module = getattr(func, "__module__", "")
    qualname = (module + ".") if module not in ("builtins", "") else ""
    return qualname + getattr(func, "__qualname__", repr(func))
