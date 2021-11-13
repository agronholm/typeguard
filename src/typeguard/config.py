from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

from .exceptions import TypeCheckError, TypeCheckWarning
from .memo import TypeCheckMemo

TypecheckFailCallback = Callable[[TypeCheckError, str, TypeCheckMemo], Any]


def __getattr__(name: str) -> TypeCheckConfiguration:
    if name == 'config':
        return _config

    raise AttributeError(f"module {__name__} has no attribute {name}")


class ForwardRefPolicy(Enum):
    """Defines how unresolved forward references are handled."""

    ERROR = 1  #: propagate the :exc:`NameError` from :func:`~typing.get_type_hints`
    WARN = 2  #: remove the annotation and emit a TypeHintWarning
    #: replace the annotation with the argument's class if the qualified name matches, else remove
    #: the annotation
    GUESS = 3


def warn_on_error(exc: TypeCheckError, argname, memo: TypeCheckMemo) -> Any:
    warnings.warn(TypeCheckWarning(f'{argname} {exc}'))


def raise_on_error(exc: TypeCheckError, argname, memo: TypeCheckMemo) -> Any:
    raise TypeCheckError(f'{argname} {exc}') from None


class TypeguardPlugin:
    def get_checker(self, annotation: Any) -> Optional[Callable[..., Any]]:
        pass


@dataclass
class TypeCheckConfiguration:
    forward_ref_policy: ForwardRefPolicy = ForwardRefPolicy.GUESS
    typecheck_fail_callback: TypecheckFailCallback = raise_on_error


_config = TypeCheckConfiguration()
