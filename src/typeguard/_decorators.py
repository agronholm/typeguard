from __future__ import annotations

import ast
import inspect
import sys
from collections.abc import Sequence
from functools import partial, wraps
from inspect import (
    Parameter,
    isasyncgenfunction,
    isclass,
    iscoroutinefunction,
    isfunction,
    isgeneratorfunction,
    signature,
)
from types import CellType, CodeType, FrameType, FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ForwardRef,
    TypeVar,
    cast,
    get_type_hints,
    overload,
)
from warnings import warn

from ._config import CollectionCheckStrategy, ForwardRefPolicy, global_config
from ._exceptions import InstrumentationWarning
from ._functions import (
    TypeCheckFailCallback,
    check_argument_types_internal,
    check_return_type_internal,
)
from ._memo import TypeCheckMemo
from ._transformer import TypeguardTransformer
from ._utils import Unset, function_name, get_stacklevel, is_method_of, unset

T_CallableOrType = TypeVar("T_CallableOrType", bound=Callable[..., Any])

if TYPE_CHECKING:

    def typeguard_ignore(arg: T_CallableOrType) -> T_CallableOrType:
        """This decorator is a noop during static type-checking."""
        return arg

else:
    from typing import no_type_check as typeguard_ignore  # noqa: F401


def make_cell(value: object) -> CellType:
    return (lambda: value).__closure__[0]  # type: ignore[index]


def find_target_function(
    new_code: CodeType, target_path: Sequence[str], firstlineno: int
) -> CodeType | None:
    for const in new_code.co_consts:
        if isinstance(const, CodeType):
            new_path = (
                target_path[1:] if const.co_name == target_path[0] else target_path
            )
            if not new_path:
                if const.co_firstlineno == firstlineno:
                    return const

                continue

            if target_code := find_target_function(const, new_path, firstlineno):
                return target_code

    return None


def is_assertion_rewritten(f: FunctionType) -> bool:
    """
    Return ``True`` if the module that defines *f* was rewritten by pytest's assertion
    rewriter.

    pytest's rewriter injects ``@pytest_ar`` and ``@py_builtins`` into the global
    namespace of every module it processes. When that marker is present, ``f.__code__``
    is not what :func:`compile` would produce from the source file, so recompiling the
    function from source (which is what :func:`instrument` does) would silently drop the
    assertion rewriting -- exactly the problem reported in
    `#477 <https://github.com/agronholm/typeguard/issues/477>`__.
    """
    module = sys.modules.get(f.__module__) if f.__module__ else None
    return module is not None and "@pytest_ar" in vars(module)


def wrap_with_type_checks(f: FunctionType) -> FunctionType:
    """
    Wrap *f* so that its arguments and return value are type checked, without replacing
    its code object.

    This is used for functions defined in modules that pytest has rewritten: the wrapper
    leaves the (rewritten) function body untouched, so assertion introspection keeps
    working, at the cost of one additional stack frame and of not checking assignments to
    annotated local variables (those checks need the AST rewriting that
    :func:`instrument` performs).
    """
    sig = signature(f, eval_str=True, globals=f.__globals__)
    type_hints = get_type_hints(f, f.__globals__)
    checkable_arguments: dict[str, Any] = {}
    for param in sig.parameters.values():
        annotation = type_hints.get(param.name, param.annotation)
        if annotation is Parameter.empty or annotation is Any:
            continue
        elif param.kind is Parameter.VAR_POSITIONAL:
            annotation = tuple[annotation, ...]  # type: ignore[valid-type]
        elif param.kind is Parameter.VAR_KEYWORD:
            annotation = dict[str, annotation]  # type: ignore[valid-type]

        checkable_arguments[param.name] = annotation

    return_annotation = type_hints.get("return", Parameter.empty)
    self_name = next(iter(sig.parameters), None)

    def check_arguments(args: tuple[Any, ...], kwargs: dict[str, Any]) -> TypeCheckMemo:
        memo = TypeCheckMemo(f.__globals__, {})
        if checkable_arguments:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            if self_name in bound.arguments:
                self_value = bound.arguments[self_name]
                memo.self_type = self_value if isclass(self_value) else type(self_value)

            arguments = {
                name: (bound.arguments[name], annotation)
                for name, annotation in checkable_arguments.items()
                if name in bound.arguments
            }
            check_argument_types_internal(f.__name__, arguments, memo)

        return memo

    def check_return(retval: Any, memo: TypeCheckMemo) -> Any:
        if return_annotation is Parameter.empty:
            return retval

        return check_return_type_internal(f.__name__, retval, return_annotation, memo)

    if iscoroutinefunction(f):

        @wraps(f)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            memo = check_arguments(args, kwargs)
            return check_return(await f(*args, **kwargs), memo)

    else:

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            memo = check_arguments(args, kwargs)
            return check_return(f(*args, **kwargs), memo)

    return wrapper  # type: ignore[return-value]


def has_annotated_locals(f: FunctionType) -> bool:
    """Return ``True`` if *f* assigns annotated local variables somewhere in its body."""
    module = sys.modules.get(f.__module__) if f.__module__ else None
    if module is None:
        return True

    target_path = [item for item in f.__qualname__.split(".") if item != "<locals>"]
    try:
        module_ast = ast.parse(inspect.getsource(module))
        instrumentor = TypeguardTransformer(target_path, f.__code__.co_firstlineno)
        instrumentor.visit(module_ast)
        target_node = instrumentor.target_node
    except (OSError, SyntaxError, TypeError):
        return True

    if target_node is None:
        return True

    return any(
        isinstance(node, ast.AnnAssign) and node.value is not None
        for node in ast.walk(target_node)
    )


def instrument_or_wrap(f: FunctionType) -> FunctionType | str:
    """
    Instrument *f*, unless instrumenting it would discard the assertion rewriting applied
    to its module by pytest while adding nothing that a wrapper cannot provide.

    Recompiling the function from source (what :func:`instrument` does) throws away the
    assertion introspection that pytest's rewriter added, so for functions that contain
    rewritten assertions but no assignments to annotated local variables, a wrapper is a
    strictly better trade: the assertions stay introspectable and the arguments and
    return value are still checked. Functions that do assign annotated locals keep being
    instrumented, since only AST rewriting can check those.
    """
    if (
        not isgeneratorfunction(f)
        and not isasyncgenfunction(f)
        and f.__qualname__ == f.__name__
        and f.__name__.startswith("test")
        and is_assertion_rewritten(f)
        and not has_annotated_locals(f)
    ):
        try:
            return wrap_with_type_checks(f)
        except (NameError, TypeError):
            # The annotations could not be resolved outside of the instrumented code, so
            # fall back to the previous behavior
            pass

    return instrument(f)


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
    instrumentor = TypeguardTransformer(target_path, f.__code__.co_firstlineno)
    instrumentor.visit(module_ast)

    if not instrumentor.target_node or instrumentor.target_lineno is None:
        return "instrumentor did not find the target function"

    module_code = compile(module_ast, f.__code__.co_filename, "exec", dont_inherit=True)
    new_code = find_target_function(
        module_code, target_path, instrumentor.target_lineno
    )
    if not new_code:
        return "cannot find the target function in the AST"

    if global_config.debug_instrumentation:
        # Find the matching AST node, then unparse it to source and print to stdout
        print(
            f"Source code of {f.__qualname__}() after instrumentation:"
            "\n----------------------------------------------",
            file=sys.stderr,
        )
        print(ast.unparse(instrumentor.target_node), file=sys.stderr)
        print(
            "----------------------------------------------",
            file=sys.stderr,
        )

    closure = f.__closure__
    if new_code.co_freevars != f.__code__.co_freevars:
        # Create a new closure and find values for the new free variables
        frame = cast(FrameType, inspect.currentframe())
        frame = cast(FrameType, frame.f_back)
        frame_locals = cast(FrameType, frame.f_back).f_locals
        cells: list[CellType] = []
        for key in new_code.co_freevars:
            if key in instrumentor.names_used_in_annotations:
                # Find the value and make a new cell from it
                value = frame_locals.get(key) or ForwardRef(key)
                cells.append(make_cell(value))
            else:
                # Reuse the cell from the existing closure
                assert f.__closure__
                cells.append(f.__closure__[f.__code__.co_freevars.index(key)])

        closure = tuple(cells)

    new_function = FunctionType(new_code, f.__globals__, f.__name__, closure=closure)
    new_function.__module__ = f.__module__
    new_function.__name__ = f.__name__
    new_function.__qualname__ = f.__qualname__
    new_function.__doc__ = f.__doc__
    new_function.__defaults__ = f.__defaults__
    new_function.__kwdefaults__ = f.__kwdefaults__

    if sys.version_info >= (3, 12):
        new_function.__type_params__ = f.__type_params__

    if sys.version_info >= (3, 14):
        new_function.__annotate__ = f.__annotate__
    else:
        new_function.__annotations__ = f.__annotations__

    return new_function


@overload
def typechecked(
    *,
    forward_ref_policy: ForwardRefPolicy | Unset = unset,
    typecheck_fail_callback: TypeCheckFailCallback | Unset = unset,
    collection_check_strategy: CollectionCheckStrategy | Unset = unset,
    debug_instrumentation: bool | Unset = unset,
) -> Callable[[T_CallableOrType], T_CallableOrType]: ...


@overload
def typechecked(target: T_CallableOrType) -> T_CallableOrType: ...


def typechecked(
    target: T_CallableOrType | None = None,
    *,
    forward_ref_policy: ForwardRefPolicy | Unset = unset,
    typecheck_fail_callback: TypeCheckFailCallback | Unset = unset,
    collection_check_strategy: CollectionCheckStrategy | Unset = unset,
    debug_instrumentation: bool | Unset = unset,
) -> Any:
    """
    Instrument the target function to perform run-time type checking.

    This decorator recompiles the target function, injecting code to type check
    arguments, return values, yield values (excluding ``yield from``) and assignments to
    annotated local variables.

    .. note:: In modules that pytest's assertion rewriter processes (i.e. test modules),
        module level ``test*`` functions are wrapped rather than recompiled. Recompiling
        them from source would drop the assertion rewriting, turning a failing ``assert``
        into a bare ``AssertionError``; wrapping keeps the introspection, at the cost of
        one extra stack frame and of not checking assignments to annotated local variables
        in those functions.

    This can also be used as a class decorator. This will instrument all type annotated
    methods, including :func:`@classmethod <classmethod>`,
    :func:`@staticmethod <staticmethod>`,  and :class:`@property <property>` decorated
    methods in the class.

    .. note:: When Python is run in optimized mode (``-O`` or ``-OO``, this decorator
        is a no-op). This is a feature meant for selectively introducing type checking
        into a code base where the checks aren't meant to be run in production.

    :param target: the function or class to enable type checking for
    :param forward_ref_policy: override for
        :attr:`.TypeCheckConfiguration.forward_ref_policy`
    :param typecheck_fail_callback: override for
        :attr:`.TypeCheckConfiguration.typecheck_fail_callback`
    :param collection_check_strategy: override for
        :attr:`.TypeCheckConfiguration.collection_check_strategy`
    :param debug_instrumentation: override for
        :attr:`.TypeCheckConfiguration.debug_instrumentation`

    """
    if target is None:
        return partial(
            typechecked,
            forward_ref_policy=forward_ref_policy,
            typecheck_fail_callback=typecheck_fail_callback,
            collection_check_strategy=collection_check_strategy,
            debug_instrumentation=debug_instrumentation,
        )

    if not __debug__:
        return target

    if isclass(target):
        for key, attr in target.__dict__.items():
            if is_method_of(attr, target):
                retval = instrument_or_wrap(cast(FunctionType, attr))
                if isfunction(retval):
                    setattr(target, key, retval)
            elif isinstance(attr, (classmethod, staticmethod)):
                if is_method_of(attr.__func__, target):
                    retval = instrument_or_wrap(cast(FunctionType, attr.__func__))
                    if isfunction(retval):
                        wrapper = attr.__class__(retval)
                        setattr(target, key, wrapper)
            elif isinstance(attr, property):
                kwargs: dict[str, Any] = {"doc": attr.__doc__}
                for name in ("fset", "fget", "fdel"):
                    property_func = kwargs[name] = getattr(attr, name)
                    if is_method_of(property_func, target):
                        retval = instrument_or_wrap(cast(FunctionType, property_func))
                        if isfunction(retval):
                            kwargs[name] = retval

                setattr(target, key, attr.__class__(**kwargs))

        return target

    # Find either the first Python wrapper or the actual function
    wrapper_class: type[classmethod[Any, Any, Any] | staticmethod[Any, Any]] | None
    wrapper_class = None
    if isinstance(target, (classmethod, staticmethod)):
        wrapper_class = target.__class__
        target = target.__func__  # type: ignore[assignment]

    retval = instrument_or_wrap(cast(FunctionType, target))
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
