from __future__ import annotations

import os
import sys
import warnings
from dataclasses import InitVar, dataclass, field
from enum import Enum, auto
from typing import Any, Callable, List, Optional, Sequence

from ._exceptions import TypeCheckError, TypeCheckWarning
from .checkers import TypeCheckLookupCallback
from .memo import TypeCheckMemo
from .utils import qualified_name

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
else:
    from importlib_metadata import entry_points

TypeCheckFailCallback = Callable[[TypeCheckError, TypeCheckMemo], Any]


def __getattr__(name: str) -> TypeCheckConfiguration:
    if name == 'config':
        return _config

    raise AttributeError(f"module {__name__} has no attribute {name}")


class ForwardRefPolicy(Enum):
    """Defines how unresolved forward references are handled."""

    ERROR = auto()  #: propagate the :exc:`NameError` when the forward reference lookup fails
    WARN = auto()  #: emit a TypeHintWarning if the forward reference lookup fails
    IGNORE = auto()  #: silently skip checks for unresolveable forward references


def warn_on_error(exc: TypeCheckError, memo: TypeCheckMemo) -> Any:
    """Emit a warning on a type mismatch."""
    warnings.warn(TypeCheckWarning(str(exc)))


@dataclass
class TypeCheckConfiguration:
    autoload_plugins: InitVar[Optional[bool]] = None
    plugins: InitVar[Optional[Sequence[str]]] = None
    forward_ref_policy: ForwardRefPolicy = ForwardRefPolicy.WARN
    checker_lookup_functions: List[TypeCheckLookupCallback] = field(default_factory=list)
    typecheck_fail_callback: Optional[TypeCheckFailCallback] = None

    def __post_init__(self, autoload_plugins: Optional[bool],
                      plugins: Optional[Sequence[str]]) -> None:
        from typeguard.checkers import builtin_checker_lookup

        self.checker_lookup_functions.append(builtin_checker_lookup)

        if autoload_plugins is None:
            autoload_plugins = 'TYPEGUARD_DISABLE_PLUGIN_AUTOLOAD' not in os.environ

        if autoload_plugins or plugins:
            for ep in entry_points(group='typeguard.checker_lookup'):
                if (autoload_plugins and plugins is None) or (plugins and ep.name in plugins):
                    try:
                        plugin = ep.load()
                    except Exception as exc:
                        warnings.warn(
                            f'Failed to load plugin {ep.name!r}: {qualified_name(exc)}: {exc}')
                        continue

                    if not callable(plugin):
                        warnings.warn(f'Plugin {ep} returned a non-callable object: {plugin!r}')
                        continue

                    self.checker_lookup_functions.insert(0, plugin)


_config = TypeCheckConfiguration()
