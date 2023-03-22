from __future__ import annotations

import ast
import inspect
import sys
from inspect import isclass, isfunction
from types import CodeType, FunctionType
from typing import TYPE_CHECKING, Any, Callable, TypeVar, overload
from warnings import warn

from ._config import global_config
from ._exceptions import InstrumentationWarning
from ._transformer import TypeguardTransformer
from ._utils import function_name, get_stacklevel, is_method_of

if TYPE_CHECKING:
    from typeshed.stdlib.types import _Cell

    _F = TypeVar("_F")

    def typeguard_ignore(f: _F) -> _F:
        """This decorator is a noop during static type-checking."""
        return f

else:
    from typing import no_type_check as typeguard_ignore  # noqa: F401

T_CallableOrType = TypeVar("T_CallableOrType", bound=Callable[..., Any])


def make_cell() -> _Cell:
    value = None
    return (lambda: value).__closure__[0]  # type: ignore[index]


def instrument(f: T_CallableOrType) -> FunctionType | str:
    if not getattr(f, "__code__", None):
        return "no code associated"
    elif not getattr(f, "__module__", None):
        return "__module__ attribute is not set"
    elif f.__code__.co_filename == "<stdin>":
        return "cannot instrument functions defined in a REPL"
    elif hasattr(f, "__wrapped__"):
        return (
            "@typechecked only supports instrumenting functions wrapped with "
            "@classmethod, @staticmethod or @property"
        )

    target_path = [item for item in f.__qualname__.split(".") if item != "<locals>"]
    module_source = inspect.getsource(sys.modules[f.__module__])
    module_ast = ast.parse(module_source)
    instrumentor = TypeguardTransformer(target_path)
    instrumentor.visit(module_ast)

    if global_config.debug_instrumentation and sys.version_info >= (3, 9):
        # Find the matching AST node, then unparse it to source and print to stdout
        level = 0
        for node in ast.walk(module_ast):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                if node.name == target_path[level]:
                    if level == len(target_path) - 1:
                        print(
                            f"Source code of {f.__qualname__}() after instrumentation:"
                            "\n----------------------------------------------",
                            file=sys.stderr,
                        )
                        print(ast.unparse(node), file=sys.stderr)
                        print(
                            "----------------------------------------------",
                            file=sys.stderr,
                        )
                    else:
                        level += 1

    module_code = compile(module_ast, f.__code__.co_filename, "exec", dont_inherit=True)
    new_code = module_code
    for name in target_path:
        for const in new_code.co_consts:
            if isinstance(const, CodeType):
                if const.co_name == name:
                    new_code = const
                    break
        else:
            return "cannot find the target function in the AST"

    cell = None
    if new_code.co_freevars == f.__code__.co_freevars:
        # The existing closure works fine
        closure = f.__closure__
    elif f.__closure__ is not None:
        # Existing closure needs modifications
        cell = make_cell()
        index = new_code.co_freevars.index(f.__name__)
        closure = f.__closure__[:index] + (cell,) + f.__closure__[index:]
    else:
        # Make a brand new closure
        cell = make_cell()
        closure = (cell,)

    new_function = FunctionType(new_code, f.__globals__, f.__name__, closure=closure)
    if cell is not None:
        cell.cell_contents = new_function

    new_function.__module__ = f.__module__
    new_function.__name__ = f.__name__
    new_function.__qualname__ = f.__qualname__
    new_function.__annotations__ = f.__annotations__
    new_function.__doc__ = f.__doc__
    new_function.__defaults__ = f.__defaults__
    new_function.__kwdefaults__ = f.__kwdefaults__
    new_function.__globals__[f.__name__] = new_function
    return new_function


@overload
def typechecked() -> Callable[[T_CallableOrType], T_CallableOrType]:
    ...


@overload
def typechecked(target: T_CallableOrType) -> T_CallableOrType:
    ...


def typechecked(target: T_CallableOrType | None = None) -> Any:
    """
    Instrument the target function to perform run-time type checking.

    This decorator recompiles the target function, injecting code to type check
    arguments, return values, yield values (excluding ``yield from``) and assignments to
    annotated local variables.

    This can also be used as a class decorator. This will instrument all type annotated
    methods, including :func:`@classmethod <classmethod>`,
    :func:`@staticmethod <staticmethod>`,  and :class:`@property <property>` decorated
    methods in the class.

    :param target: the function or class to enable type checking for

    """
    if target is None:
        return typechecked

    if isclass(target):
        for key, attr in target.__dict__.items():
            if is_method_of(attr, target):
                retval = instrument(attr)
                if isfunction(retval):
                    setattr(target, key, retval)
            elif isinstance(attr, (classmethod, staticmethod)):
                if is_method_of(attr.__func__, target):
                    retval = instrument(attr.__func__)
                    if isfunction(retval):
                        wrapper = attr.__class__(retval)
                        setattr(target, key, wrapper)
            elif isinstance(attr, property):
                kwargs: dict[str, Any] = dict(doc=attr.__doc__)
                for name in ("fset", "fget", "fdel"):
                    property_func = kwargs[name] = getattr(attr, name)
                    if is_method_of(property_func, target):
                        retval = instrument(property_func)
                        if isfunction(retval):
                            kwargs[name] = retval

                setattr(target, key, attr.__class__(**kwargs))

        return target

    # Find either the first Python wrapper or the actual function
    wrapper_class: type[classmethod[Any]] | type[staticmethod[Any]] | None = None
    if isinstance(target, (classmethod, staticmethod)):
        wrapper_class = target.__class__
        target = target.__func__

    retval = instrument(target)
    if isinstance(retval, str):
        warn(
            f"{retval} -- not typechecking {function_name(target)}",
            InstrumentationWarning,
            stacklevel=get_stacklevel(),
        )
        return target

    if wrapper_class is None:
        return retval
    else:
        return wrapper_class(retval)
