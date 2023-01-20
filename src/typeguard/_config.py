from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._functions import TypeCheckFailCallback


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


@dataclass
class TypeCheckConfiguration:
    """
     You can change Typeguard's behavior with these settings.

    .. attribute:: typecheck_fail_callback
       :type: Callable[[TypeCheckError, TypeCheckMemo], Any]

         Callable that is called when type checking fails.

    .. attribute:: forward_ref_policy
       :type: ForwardRefPolicy

         Specifies what to do when a forward reference fails to resolve.
    """

    forward_ref_policy: ForwardRefPolicy = ForwardRefPolicy.WARN
    typecheck_fail_callback: TypeCheckFailCallback | None = None


global_config = TypeCheckConfiguration()
