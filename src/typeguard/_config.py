from __future__ import annotations

import sys
import warnings
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable

from ._exceptions import TypeCheckError, TypeCheckWarning
from ._memo import TypeCheckMemo

if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

TypeCheckFailCallback: TypeAlias = Callable[[TypeCheckError, TypeCheckMemo], Any]


class ForwardRefPolicy(Enum):
    """
    Defines how unresolved forward references are handled.

    Members:

    * ``ERROR``: propagate the :exc:`NameError` when the forward reference lookup fails
    * ``WARN``: emit a :class:`~.TypeHintWarning` if the forward reference lookup fails
    * ``IGNORE``: silently skip checks for unresolveable forward references
    """

    ERROR = auto()
    WARN = auto()
    IGNORE = auto()


def warn_on_error(exc: TypeCheckError, memo: TypeCheckMemo) -> Any:
    """
    Emit a warning on a type mismatch.

    This is intended to be used as an error handler in ``typecheck_fail_callback``.

    """
    warnings.warn(TypeCheckWarning(str(exc)))


@dataclass
class TypeCheckConfiguration:
    """
    You can change Typeguard's behavior with these settings.

    :var ForwardRefPolicy forward_ref_policy: specifies what to do when a forward
        reference fails to resolve
    :var TypeCheckFailCallback typecheck_fail_callback: callable that is called when
        type checking fails
    """

    forward_ref_policy: ForwardRefPolicy = ForwardRefPolicy.WARN
    typecheck_fail_callback: TypeCheckFailCallback | None = None
