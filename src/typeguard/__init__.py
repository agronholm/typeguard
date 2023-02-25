__all__ = (
    "CallMemo",
    "CollectionCheckStrategy",
    "ForwardRefPolicy",
    "ImportHookManager",
    "TypeCheckerCallable",
    "TypeCheckFailCallback",
    "TypeCheckLookupCallback",
    "TypeCheckConfiguration",
    "TypeHintWarning",
    "TypeCheckWarning",
    "TypeCheckError",
    "TypeCheckMemo",
    "TypeguardFinder",
    "check_type",
    "check_type_internal",
    "checker_lookup_functions",
    "config",
    "install_import_hook",
    "load_plugins",
    "suppress_type_checks",
    "typechecked",
    "typeguard_ignore",
    "warn_on_error",
)

import os
from typing import Any

from ._checkers import (
    TypeCheckerCallable,
    TypeCheckLookupCallback,
    check_type_internal,
    checker_lookup_functions,
    load_plugins,
)
from ._config import CollectionCheckStrategy, ForwardRefPolicy, TypeCheckConfiguration
from ._config import global_config as _global_config
from ._decorators import typechecked, typeguard_ignore
from ._exceptions import TypeCheckError, TypeCheckWarning, TypeHintWarning
from ._functions import (
    TypeCheckFailCallback,
    check_type,
    suppress_type_checks,
    warn_on_error,
)
from ._importhook import ImportHookManager, TypeguardFinder, install_import_hook
from ._memo import CallMemo, TypeCheckMemo

# Re-export imports so they look like they live directly in this package
for value in list(locals().values()):
    if getattr(value, "__module__", "").startswith(f"{__name__}."):
        value.__module__ = __name__


config: TypeCheckConfiguration


def __getattr__(name: str) -> Any:
    if name == "config":
        return _global_config


# Automatically load checker lookup functions unless explicitly disabled
if "TYPEGUARD_DISABLE_PLUGIN_AUTOLOAD" not in os.environ:
    load_plugins()
