from __future__ import annotations

import ast
import inspect
import sys
from functools import partial, update_wrapper
from inspect import isclass
from types import CodeType, FunctionType
from typing import TYPE_CHECKING, Any, Callable, TypeVar, overload
from warnings import warn

from ._config import TypeCheckConfiguration
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
DUMMY_FUNC_NAME = "__typeguard_dummy_func"


class Instrumentor(ast.NodeTransformer):
    def __init__(self, target_name: str):
        self._target_path = [
            item for item in target_name.split(".") if item != "<locals>"
        ]
        self._path: list[str] = []
        self._transformer = TypeguardTransformer()
        self._typeguard_import_name: str | None = None
        self._typechecked_import_name: str | None = None
        self._parent: ast.ClassDef | ast.FunctionDef | None = None

    def visit_Module(self, node: ast.Module) -> Any:
        self.generic_visit(node)
        ast.fix_missing_locations(node)
        return node

    def visit_Import(self, node: ast.Import) -> ast.Import:
        for name in node.names:
            if name.name == "typeguard":
                self._typeguard_import_name = name.asname or name.name

        return node

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        if node.module == "typeguard":
            for name in node.names:
                if name.name == "typechecked":
                    self._typechecked_import_name = name.asname or name.name

        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef | None:
        # Eliminate top level classes not belonging to the target path
        if not self._path and node.name != self._target_path[0]:
            return None

        self._path.append(node.name)
        previous_parent = self._parent
        self._parent = node
        self.generic_visit(node)
        self._parent = previous_parent
        del self._path[-1]
        return node

    def visit_FunctionDef(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        # Eliminate top level functions not belonging to the target path
        if not self._path and node.name != self._target_path[0]:
            return None

        self._path.append(node.name)
        previous_parent = self._parent
        self._parent = node
        self.generic_visit(node)
        self._parent = previous_parent
        if self._path == self._target_path:
            has_self_arg = isinstance(self._parent, ast.ClassDef)
            node = self._transformer.visit_FunctionDef(node, has_self_arg=has_self_arg)
            node.body.insert(0, ast.Import([ast.alias("typeguard")]))

            # Remove both @typeguard.typechecked and @typechecked (while taking aliased
            # imports into account)
            for decorator in node.decorator_list.copy():
                if self._typechecked_import_name and isinstance(decorator, ast.Name):
                    if decorator.id == self._typechecked_import_name:
                        node.decorator_list.remove(decorator)
                elif self._typeguard_import_name and isinstance(
                    decorator, ast.Attribute
                ):
                    if isinstance(decorator.value, ast.Name):
                        if decorator.value.id == self._typeguard_import_name:
                            if decorator.attr == "typechecked":
                                node.decorator_list.remove(decorator)

        del self._path[-1]
        return node

    def visit_AsyncFunctionDef(
        self, node: ast.AsyncFunctionDef
    ) -> ast.AsyncFunctionDef:
        return self.visit_FunctionDef(node)


def make_cell():
    value = None
    return (lambda: value).__closure__[0]


def instrument(f: T_CallableOrType) -> Callable | str:
    if not getattr(f, "__annotations__", None):
        return "no type annotations present"
    elif not getattr(f, "__code__", None):
        return "no code associated"
    elif not getattr(f, "__module__", None):
        return "__module__ attribute is not set"

    module = sys.modules[f.__module__]
    module_source = inspect.getsource(sys.modules[f.__module__])
    module_ast = ast.parse(module_source)
    instrumentor = Instrumentor(f.__qualname__)
    instrumentor.visit(module_ast)
    module_code = compile(module_ast, module.__file__, "exec", dont_inherit=True)
    new_code = module_code
    for level, name in enumerate(instrumentor._target_path):
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
        assert new_code.co_freevars == (f.__name__,)
        cell = make_cell()
        closure = (cell,)

    new_function = FunctionType(new_code, f.__globals__, f.__name__, closure=closure)
    if cell is not None:
        cell.cell_contents = new_function

    update_wrapper(new_function, f)
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
