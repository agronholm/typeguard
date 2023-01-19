__all__ = (
    "CallMemo",
    "ForwardRefPolicy",
    "TypeCheckerCallable",
    "TypeCheckFailCallback",
    "TypeCheckLookupCallback",
    "TypeCheckConfiguration",
    "TypeHintWarning",
    "TypeCheckWarning",
    "TypeCheckError",
    "TypeCheckMemo",
    "check_argument_types",
    "check_return_type",
    "check_type",
    "check_type_internal",
    "checker_lookup_functions",
    "config",
    "load_plugins",
    "suppress_type_checks",
    "typechecked",
    "typeguard_ignore",
    "warn_on_error",
)

import os
import sys
from typing import Any

from ._checkers import (
    TypeCheckerCallable,
    TypeCheckLookupCallback,
    check_type_internal,
    checker_lookup_functions,
    load_plugins,
)
from ._config import (
    ForwardRefPolicy,
    TypeCheckConfiguration,
    TypeCheckFailCallback,
    warn_on_error,
)
from ._decorators import typechecked, typeguard_ignore
from ._exceptions import TypeCheckError, TypeCheckWarning, TypeHintWarning
from ._functions import (
    check_argument_types,
    check_return_type,
    check_type,
    suppress_type_checks,
)
from ._memo import CallMemo, TypeCheckMemo

if sys.version_info >= (3, 8):
    from typing import Final
else:
    from typing_extensions import Final

# Re-export imports so they look like they live directly in this package
for value in list(locals().values()):
    if getattr(value, "__module__", "").startswith(f"{__name__}."):
        value.__module__ = __name__


config: TypeCheckConfiguration
_config: Final[TypeCheckConfiguration] = TypeCheckConfiguration()


def __getattr__(name: str) -> Any:
    if name == "config":
        return _config


# Automatically load checker lookup functions unless explicitly disabled
if "TYPEGUARD_DISABLE_PLUGIN_AUTOLOAD" not in os.environ:
    load_plugins()
