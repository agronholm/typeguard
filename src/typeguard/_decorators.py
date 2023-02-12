from __future__ import annotations

import ast
import inspect
import sys
from functools import partial
from inspect import isclass
from types import CodeType, FunctionType
from typing import TYPE_CHECKING, Any, Callable, TypeVar, overload
from warnings import warn

from ._config import TypeCheckConfiguration, global_config
from ._exceptions import InstrumentationWarning
from ._transformer import TypeguardTransformer
from ._utils import function_name

if TYPE_CHECKING:
    _F = TypeVar("_F")

    def typeguard_ignore(f: _F) -> _F:
        """This decorator is a noop during static type-checking."""
        return f

else:
    from typing import no_type_check as typeguard_ignore  # noqa: F401

T_CallableOrType = TypeVar("T_CallableOrType", bound=Callable[..., Any])


def make_cell():
    value = None
    return (lambda: value).__closure__[0]


def instrument(f: T_CallableOrType) -> Callable | str:
    if not getattr(f, "__code__", None):
        return "no code associated"
    elif not getattr(f, "__module__", None):
        return "__module__ attribute is not set"
    elif f.__code__.co_filename == "<stdin>":
        return "cannot instrument functions defined in a REPL"

    target_path = [item for item in f.__qualname__.split(".") if item != "<locals>"]
    module = sys.modules[f.__module__]
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

    module_code = compile(module_ast, module.__file__, "exec", dont_inherit=True)
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
        assert new_code.co_freevars[0] == f.__name__
        closure = (cell,) + f.__closure__
    else:
        # Make a brand new closure
        # assert new_code.co_freevars == (f.__name__,)
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
    new_function.__globals__[f.__name__] = new_function
    return new_function


@overload
def typechecked(
    *, config: TypeCheckConfiguration | None = None
) -> Callable[[T_CallableOrType], T_CallableOrType]:
    ...


@overload
def typechecked(
    func: T_CallableOrType, *, config: TypeCheckConfiguration | None = None
) -> T_CallableOrType:
    ...


def typechecked(
    func: T_CallableOrType | None = None,
    *,
    check_arguments: bool = True,
    check_return: bool = True,
    check_yield: bool = True,
):
    """
    Perform runtime type checking on the arguments that are passed to the wrapped
    function.

    The return value is also checked against the return annotation if any.

    This can also be used as a class decorator. This will wrap all type annotated
    methods, including ``@classmethod``, ``@staticmethod``,  and ``@property``
    decorated methods, in the class with the ``@typechecked`` decorator.

    :param func: the function or class to enable type checking for
    :param check_arguments: if ``True``, perform type checks against annotated arguments
    :param check_return: if ``True``, perform type checks against any returned values
    :param check_yield: if ``True``, perform type checks against any yielded values
        (only applicable to generator functions)

    .. note:: ``yield from`` is currently not type checked.

    """
    if func is None:
        return partial(
            typechecked,
            check_arguments=check_arguments,
            check_return=check_return,
            check_yield=check_yield,
        )

    if isclass(func):
        for key, attr in func.__dict__.items():
            if (
                inspect.isfunction(attr)
                or inspect.ismethod(attr)
                or inspect.isclass(attr)
            ):
                retval = instrument(attr)
                if callable(retval):
                    setattr(func, key, retval)
            elif isinstance(attr, (classmethod, staticmethod)):
                retval = instrument(attr)
                if callable(retval):
                    setattr(func, key, retval)
            elif isinstance(attr, property):
                kwargs = dict(doc=attr.__doc__)
                for name in ("fset", "fget", "fdel"):
                    property_func = kwargs[name] = getattr(attr, name)
                    retval = instrument(property_func)
                    if callable(retval):
                        kwargs[name] = retval

                setattr(func, key, attr.__class__(**kwargs))

        return func

    # Find either the first Python wrapper or the actual function
    wrapper = None
    if isinstance(func, (classmethod, staticmethod)):
        wrapper = func.__class__
        func = func.__func__
    elif hasattr(func, "__wrapped__"):
        warn(
            f"Cannot instrument {function_name(func)} -- @typechecked only supports "
            f"instrumenting functions wrapped with @classmethod, @staticmethod or "
            f"@property",
            InstrumentationWarning,
        )
        return func

    retval = instrument(func)
    if isinstance(retval, str):
        warn(
            f"{retval} -- not typechecking {function_name(func)}",
            InstrumentationWarning,
        )
        return func

    return retval if wrapper is None else wrapper(retval)
