from __future__ import annotations

import ast
import sys
from collections.abc import Iterable
from importlib.abc import MetaPathFinder
from importlib.machinery import SourceFileLoader
from importlib.util import cache_from_source, decode_source
from inspect import isclass
from unittest.mock import patch


# The name of this function is magical
def _call_with_frames_removed(f, *args, **kwargs):
    return f(*args, **kwargs)


def optimized_cache_from_source(path, debug_override=None):
    return cache_from_source(path, debug_override, optimization="typeguard")


class TypeguardTransformer(ast.NodeTransformer):
    def __init__(self, memo_variable_name: str) -> None:
        self._memo_variable_name = memo_variable_name
        self._parents: list[ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef] = []
        self._contains_yields: set[ast.FunctionDef] = set()

    def visit_Module(self, node: ast.Module):
        # Insert "import typeguard" after any "from __future__ ..." imports
        for i, child in enumerate(node.body):
            if isinstance(child, ast.ImportFrom) and child.module == "__future__":
                continue
            elif isinstance(child, ast.Expr) and isinstance(child.value, ast.Str):
                continue  # module docstring
            else:
                node.body.insert(i, ast.Import(names=[ast.alias("typeguard", None)]))
                break

        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        self._parents.append(node)
        self.generic_visit(node)
        self._parents.pop()
        return node

    def visit_Return(self, node: ast.Return):
        if self._parents[-1].returns:
            retval = node.value or ast.Name(id="None", ctx=ast.Load())
            node = ast.Return(
                ast.Call(
                    ast.Attribute(
                        ast.Name(id="typeguard", ctx=ast.Load()),
                        "check_return_type",
                        ctx=ast.Load(),
                    ),
                    [retval, ast.Name(id=self._memo_variable_name, ctx=ast.Load())],
                    [],
                )
            )

        self.generic_visit(node)
        return node

    def visit_Yield(self, node: ast.Yield):
        self._contains_yields.add(self._parents[-1])
        if self._parents[-1].returns:
            yieldval = node.value or ast.Name(id="None", ctx=ast.Load())
            node = ast.Yield(
                ast.Call(
                    ast.Attribute(
                        ast.Name(id="typeguard", ctx=ast.Load()),
                        "check_yield_type",
                        ctx=ast.Load(),
                    ),
                    [yieldval, ast.Name(id=self._memo_variable_name, ctx=ast.Load())],
                    [],
                )
            )

        self.generic_visit(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        has_annotated_args = any(arg for arg in node.args.args if arg.annotation)
        has_annotated_return = bool(node.returns)
        if has_annotated_args or has_annotated_return:
            has_self_arg = False
            func_reference = ast.Name(id=node.name, ctx=ast.Load())
            if self._parents and isinstance(self._parents[-1], ast.ClassDef):
                # This is a method, not a free function.
                # Walk through the parents and build the attribute chain from containing
                # classes like A.B.C.methodname
                previous_attribute: ast.Attribute | None = None
                for parent_node in reversed(self._parents):
                    if isinstance(parent_node, ast.ClassDef):
                        attrname = (
                            previous_attribute.value.id
                            if previous_attribute
                            else func_reference.id
                        )
                        attribute = ast.Attribute(
                            ast.Name(id=parent_node.name, ctx=ast.Load()),
                            attrname,
                            ctx=ast.Load(),
                        )
                        if previous_attribute is None:
                            func_reference = attribute
                        else:
                            previous_attribute.value = attribute

                        previous_attribute = attribute
                    else:
                        break

                for expr in node.decorator_list:
                    if isinstance(expr, ast.Name) and expr.id == "staticmethod":
                        break
                else:
                    has_self_arg = True

            locals_call = ast.Call(ast.Name(id="locals", ctx=ast.Load()), [], [])
            memo_expr = ast.Call(
                ast.Attribute(
                    ast.Name(id="typeguard", ctx=ast.Load()), "CallMemo", ctx=ast.Load()
                ),
                [func_reference, locals_call],
                [
                    ast.keyword(
                        "has_self_arg", ast.Constant(has_self_arg, ctx=ast.Load())
                    ),
                    ast.keyword(
                        "unwrap_generator_annotations",
                        ast.Constant(True, ctx=ast.Load()),
                    ),
                ],
            )
            node.body.insert(
                0,
                ast.Assign(
                    [ast.Name(id=self._memo_variable_name, ctx=ast.Store())], memo_expr
                ),
            )

        if has_annotated_args:
            node.body.insert(
                1,
                ast.Expr(
                    ast.Call(
                        ast.Attribute(
                            ast.Name(id="typeguard", ctx=ast.Load()),
                            "check_argument_types",
                            ctx=ast.Load(),
                        ),
                        [ast.Name(id=self._memo_variable_name, ctx=ast.Load())],
                        [],
                    )
                ),
            )

        self._parents.append(node)
        self.generic_visit(node)
        self._parents.pop()

        # Add a checked "return None" to the end if there's no explicit return
        if node not in self._contains_yields:
            if has_annotated_return and not isinstance(node.body[-1], ast.Return):
                # Replace a placeholder "pass" at the end
                if isinstance(node.body[-1], ast.Pass):
                    del node.body[-1]

                node.body.append(
                    ast.Return(
                        ast.Call(
                            ast.Attribute(
                                ast.Name(id="typeguard", ctx=ast.Load()),
                                "check_return_type",
                                ctx=ast.Load(),
                            ),
                            [
                                ast.Constant(None),
                                ast.Name(id=self._memo_variable_name, ctx=ast.Load()),
                            ],
                            [],
                        )
                    ),
                )
        else:
            self._contains_yields.remove(node)

        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)
        return node


class TypeguardLoader(SourceFileLoader):
    def source_to_code(self, data, path, *, _optimize=-1):
        source = decode_source(data)

        # Find a variable name for the call memo that isn't found in the source code
        memo_variable_name = "_call_memo"
        i = 1
        while memo_variable_name in source:
            memo_variable_name = f"_call_memo_{i}"
            i += 1

        tree = _call_with_frames_removed(
            compile,
            source,
            path,
            "exec",
            ast.PyCF_ONLY_AST,
            dont_inherit=True,
            optimize=_optimize,
        )
        tree = TypeguardTransformer(memo_variable_name).visit(tree)
        ast.fix_missing_locations(tree)
        return _call_with_frames_removed(
            compile, tree, path, "exec", dont_inherit=True, optimize=_optimize
        )

    def exec_module(self, module):
        # Use a custom optimization marker – the import lock should make this monkey
        # patch safe
        with patch(
            "importlib._bootstrap_external.cache_from_source",
            optimized_cache_from_source,
        ):
            return super().exec_module(module)


class TypeguardFinder(MetaPathFinder):
    """
    Wraps another path finder and instruments the module with
    :func:`@typechecked <typeguard.typechecked>` if :meth:`should_instrument` returns
    ``True``.

    Should not be used directly, but rather via :func:`~.install_import_hook`.

    .. versionadded:: 2.6

    """

    def __init__(self, packages, original_pathfinder):
        self.packages = packages
        self._original_pathfinder = original_pathfinder

    def find_spec(self, fullname, path=None, target=None):
        if self.should_instrument(fullname):
            spec = self._original_pathfinder.find_spec(fullname, path, target)
            if spec is not None and isinstance(spec.loader, SourceFileLoader):
                spec.loader = TypeguardLoader(spec.loader.name, spec.loader.path)
                return spec

        return None

    def should_instrument(self, module_name: str) -> bool:
        """
        Determine whether the module with the given name should be instrumented.

        :param module_name: full name of the module that is about to be imported (e.g.
            ``xyz.abc``)

        """
        for package in self.packages:
            if module_name == package or module_name.startswith(package + "."):
                return True

        return False


class ImportHookManager:
    """
    A handle that can be used to uninstall the Typeguard import hook.
    """

    def __init__(self, hook: MetaPathFinder):
        self.hook = hook

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.uninstall()

    def uninstall(self) -> None:
        """Uninstall the import hook."""
        try:
            sys.meta_path.remove(self.hook)
        except ValueError:
            pass  # already removed


def install_import_hook(
    packages: Iterable[str], *, cls: type[TypeguardFinder] = TypeguardFinder
) -> ImportHookManager:
    """
    Install an import hook that decorates classes and functions with
    :func:`@typechecked <typeguard.typechecked>`.

    This only affects modules loaded **after** this hook has been installed.

    :return: a context manager that uninstalls the hook on exit (or when you call
        ``.uninstall()``)

    .. versionadded:: 2.6

    """
    if isinstance(packages, str):
        packages = [packages]

    for i, finder in enumerate(sys.meta_path):
        if (
            isclass(finder)
            and finder.__name__ == "PathFinder"
            and hasattr(finder, "find_spec")
        ):
            break
    else:
        raise RuntimeError("Cannot find a PathFinder in sys.meta_path")

    hook = cls(packages, finder)
    sys.meta_path.insert(0, hook)
    return ImportHookManager(hook)
