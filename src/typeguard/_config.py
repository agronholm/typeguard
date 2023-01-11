from __future__ import annotations

import os
import sys
import warnings
from dataclasses import InitVar, dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Sequence

from ._checkers import TypeCheckLookupCallback
from ._exceptions import TypeCheckError, TypeCheckWarning
from ._memo import TypeCheckMemo
from ._utils import qualified_name

if sys.version_info >= (3, 10):
    from importlib.metadata import entry_points
    from typing import TypeAlias
else:
    from importlib_metadata import entry_points
    from typing_extensions import TypeAlias

TypeCheckFailCallback: TypeAlias = Callable[[TypeCheckError, TypeCheckMemo], Any]


class ForwardRefPolicy(Enum):
    """Defines how unresolved forward references are handled."""

    ERROR = (
        auto()
    )  #: propagate the :exc:`NameError` when the forward reference lookup fails
    WARN = auto()  #: emit a TypeHintWarning if the forward reference lookup fails
    IGNORE = auto()  #: silently skip checks for unresolveable forward references


def warn_on_error(exc: TypeCheckError, memo: TypeCheckMemo) -> Any:
    """Emit a warning on a type mismatch."""
    warnings.warn(TypeCheckWarning(str(exc)))


@dataclass
class TypeCheckConfiguration:
    autoload_plugins: InitVar[bool | None] = None
    plugins: InitVar[Sequence[str] | None] = None
    forward_ref_policy: ForwardRefPolicy = ForwardRefPolicy.WARN
    checker_lookup_functions: list[TypeCheckLookupCallback] = field(
        default_factory=list
    )
    typecheck_fail_callback: TypeCheckFailCallback | None = None

    def __post_init__(
        self, autoload_plugins: bool | None, plugins: Sequence[str] | None
    ) -> None:
        from typeguard._checkers import builtin_checker_lookup

        self.checker_lookup_functions.append(builtin_checker_lookup)

        if autoload_plugins is None:
            autoload_plugins = "TYPEGUARD_DISABLE_PLUGIN_AUTOLOAD" not in os.environ

        if autoload_plugins or plugins:
            for ep in entry_points(group="typeguard.checker_lookup"):
                if (autoload_plugins and plugins is None) or (
                    plugins and ep.name in plugins
                ):
                    try:
                        plugin = ep.load()
                    except Exception as exc:
                        warnings.warn(
                            f"Failed to load plugin {ep.name!r}: "
                            f"{qualified_name(exc)}: {exc}"
                        )
                        continue

                    if not callable(plugin):
                        warnings.warn(
                            f"Plugin {ep} returned a non-callable object: {plugin!r}"
                        )
                        continue

                    self.checker_lookup_functions.insert(0, plugin)


_config = TypeCheckConfiguration()
