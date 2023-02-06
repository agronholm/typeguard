from __future__ import annotations

import inspect
import sys
from types import CodeType, FunctionType
from typing import TYPE_CHECKING, Any, Callable, ForwardRef
from weakref import WeakValueDictionary

if TYPE_CHECKING:
    from ._memo import TypeCheckMemo

if sys.version_info >= (3, 10):
    from typing import get_args, get_origin

    def evaluate_forwardref(forwardref: ForwardRef, memo: TypeCheckMemo) -> Any:
        return forwardref._evaluate(memo.globals, memo.locals, frozenset())

else:
    from typing_extensions import get_args, get_origin

    evaluate_extra_args = (frozenset(),) if sys.version_info >= (3, 9) else ()

    def evaluate_forwardref(forwardref: ForwardRef, memo: TypeCheckMemo) -> Any:
        from ._union_transformer import compile_type_hint, type_substitutions

        if not forwardref.__forward_evaluated__:
            forwardref.__forward_code__ = compile_type_hint(forwardref.__forward_arg__)

        try:
            return forwardref._evaluate(memo.globals, memo.locals, *evaluate_extra_args)
        except NameError:
            if sys.version_info < (3, 9):
                # Try again, with the type substitutions (list -> List etc.) in place
                new_globals = type_substitutions.copy()
                new_globals.update(memo.globals)
                return forwardref._evaluate(
                    new_globals, memo.locals or new_globals, *evaluate_extra_args
                )

            raise


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
            formatted_args = ", ".join(repr(arg) for arg in args)
        else:
            formatted_args = ", ".join(get_type_name(arg) for arg in args)

        name += f"[{formatted_args}]"

    module = getattr(type_, "__module__", None)
    if module not in (None, "typing", "typing_extensions", "builtins"):
        name = module + "." + name

    return name


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
