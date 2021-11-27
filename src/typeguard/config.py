from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional

from .checkers import TypeCheckLookupCallback
from .exceptions import TypeCheckError, TypeCheckWarning
from .memo import TypeCheckMemo

TypeCheckFailCallback = Callable[[TypeCheckError, str, TypeCheckMemo], Any]


def __getattr__(name: str) -> TypeCheckConfiguration:
    if name == 'config':
        return _config

    raise AttributeError(f"module {__name__} has no attribute {name}")


class ForwardRefPolicy(Enum):
    """Defines how unresolved forward references are handled."""

    ERROR = 1  #: propagate the :exc:`NameError` when the forward reference lookup fails
    WARN = 2  #: emit a TypeHintWarning if the forward reference lookup fails
    IGNORE = 3  #: silently skip checks for unresolveable forward references


def warn_on_error(exc: TypeCheckError, argname, memo: TypeCheckMemo) -> Any:
    warnings.warn(TypeCheckWarning(f'{argname} {exc}'))


def raise_on_error(exc: TypeCheckError, argname, memo: TypeCheckMemo) -> Any:
    raise TypeCheckError(f'{argname} {exc}') from None


class TypeguardPlugin:
    def get_checker(self, annotation: Any) -> Optional[Callable[..., Any]]:
        pass


@dataclass
class TypeCheckConfiguration:
    forward_ref_policy: ForwardRefPolicy = ForwardRefPolicy.WARN
    checker_lookup_functions: List[TypeCheckLookupCallback] = field(default_factory=list)
    typecheck_fail_callback: TypeCheckFailCallback = raise_on_error

    def __post_init__(self):
        from typeguard.checkers import builtin_checker_lookup

        self.checker_lookup_functions.append(builtin_checker_lookup)


_config = TypeCheckConfiguration()
