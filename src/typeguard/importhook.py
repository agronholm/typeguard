import ast
import sys
from importlib.abc import MetaPathFinder, _Path
from importlib.machinery import ModuleSpec, SourceFileLoader
from importlib.util import cache_from_source, decode_source
from inspect import isclass
from types import ModuleType, TracebackType
from typing import Any, Callable, Iterable, List, Optional, Sequence, Type, Union, cast
from unittest.mock import patch


# The name of this function is magical
def _call_with_frames_removed(f: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    return f(*args, **kwargs)


def optimized_cache_from_source(path: str, debug_override: Optional[bool] = None) -> str:
    return cache_from_source(path, debug_override, optimization='typeguard')


class TypeguardTransformer(ast.NodeVisitor):
    def __init__(self) -> None:
        self._parents = []  # type: List[Union[ast.Module, ast.ClassDef, ast.FunctionDef]]

    def visit_Module(self, node: ast.Module) -> ast.Module:
        # Insert "import typeguard" after any "from __future__ ..." imports
        for i, child in enumerate(node.body):
            if isinstance(child, ast.ImportFrom) and child.module == '__future__':
                continue
            elif isinstance(child, ast.Expr) and isinstance(child.value, ast.Str):
                continue  # module docstring
            else:
                node.body.insert(i, ast.Import(names=[ast.alias('typeguard', None)]))
                break

        self._parents.append(node)
        self.generic_visit(node)
        self._parents.pop()
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        node.decorator_list.append(
            ast.Attribute(ast.Name(id='typeguard', ctx=ast.Load()), 'typechecked', ast.Load())
        )
        self._parents.append(node)
        self.generic_visit(node)
        self._parents.pop()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Let the class level decorator handle the methods of a class
        if isinstance(self._parents[-1], ast.ClassDef):
            return node

        has_annotated_args = any(arg for arg in node.args.args if arg.annotation)
        has_annotated_return = bool(node.returns)
        if has_annotated_args or has_annotated_return:
            node.decorator_list.insert(
                0,
                ast.Attribute(ast.Name(id='typeguard', ctx=ast.Load()), 'typechecked', ast.Load())
            )

        self._parents.append(node)
        self.generic_visit(node)
        self._parents.pop()
        return node


class TypeguardLoader(SourceFileLoader):
    @staticmethod
    def source_to_code(data: Union[bytes, str], path: str, *,
                       _optimize: int = -1) -> Any:  # type: ignore[override]
        source = data if isinstance(data, str) else decode_source(data)
        tree = _call_with_frames_removed(compile, source, path, 'exec', ast.PyCF_ONLY_AST,
                                         dont_inherit=True, optimize=_optimize)
        tree = TypeguardTransformer().visit(tree)
        ast.fix_missing_locations(tree)
        return _call_with_frames_removed(compile, tree, path, 'exec',
                                         dont_inherit=True, optimize=_optimize)

    def exec_module(self, module: ModuleType) -> None:
        # Use a custom optimization marker – the import lock should make this monkey patch safe
        with patch('importlib._bootstrap_external.cache_from_source', optimized_cache_from_source):
            return super().exec_module(module)


class TypeguardFinder(MetaPathFinder):
    """
    Wraps another path finder and instruments the module with ``@typechecked`` if
    :meth:`should_instrument` returns ``True``.

    Should not be used directly, but rather via :func:`~.install_import_hook`.

    .. versionadded:: 2.6

    """

    def __init__(self, packages: Iterable[str], original_pathfinder: 'TypeguardFinder') -> None:
        self.packages = packages
        self._original_pathfinder = original_pathfinder

    def find_spec(self, fullname: str, path: Optional[Sequence[_Path]] = None,
                  target: Optional[ModuleType] = None) -> Optional[ModuleSpec]:
        if self.should_instrument(fullname):
            spec = self._original_pathfinder.find_spec(fullname, path, target)
            if spec is not None and isinstance(spec.loader, SourceFileLoader):
                spec.loader = TypeguardLoader(spec.loader.name, spec.loader.path)
                return spec

        return None

    def should_instrument(self, module_name: str) -> bool:
        """
        Determine whether the module with the given name should be instrumented.

        :param module_name: full name of the module that is about to be imported (e.g. ``xyz.abc``)

        """
        for package in self.packages:
            if module_name == package or module_name.startswith(package + '.'):
                return True

        return False


class ImportHookManager:
    def __init__(self, hook: MetaPathFinder) -> None:
        self.hook = hook

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException],
                 exc_tb: Optional[TracebackType]) -> None:
        self.uninstall()

    def uninstall(self) -> None:
        try:
            sys.meta_path.remove(self.hook)
        except ValueError:
            pass  # already removed


def install_import_hook(packages: Iterable[str], *,
                        cls: Type[TypeguardFinder] = TypeguardFinder) -> ImportHookManager:
    """
    Install an import hook that decorates classes and functions with ``@typechecked``.

    This only affects modules loaded **after** this hook has been installed.

    :return: a context manager that uninstalls the hook on exit (or when you call ``.uninstall()``)

    .. versionadded:: 2.6

    """
    if isinstance(packages, str):
        packages = [packages]

    for i, finder in enumerate(sys.meta_path):
        if isclass(finder) and finder.__name__ == 'PathFinder' and hasattr(finder, 'find_spec'):
            break
    else:
        raise RuntimeError('Cannot find a PathFinder in sys.meta_path')

    hook = cls(packages, cast(TypeguardFinder, finder))
    sys.meta_path.insert(0, hook)
    return ImportHookManager(hook)
