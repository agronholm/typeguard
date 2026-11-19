from __future__ import annotations

from typing import Any

from typeguard._config import TypeCheckConfiguration, global_config


def _is_typeguard_internal(value: Any) -> bool:
    module: str = getattr(value, "__module__", None) or ""
    return module == "typeguard" or module.startswith("typeguard.")


class TypeCheckMemo:
    """
    Contains information necessary for type checkers to do their work.

    .. attribute:: globals
       :type: dict[str, Any]

        Dictionary of global variables to use for resolving forward references.

    .. attribute:: locals
       :type: dict[str, Any]

        Dictionary of local variables to use for resolving forward references.

    .. attribute:: self_type
       :type: type | None

        When running type checks within an instance method or class method, this is the
        class object that the first argument (usually named ``self`` or ``cls``) refers
        to.

    .. attribute:: config
       :type: TypeCheckConfiguration

         Contains the configuration for a particular set of type checking operations.
    """

    __slots__ = "config", "globals", "locals", "self_type"

    def __init__(
        self,
        globals: dict[str, Any],
        locals: dict[str, Any],
        *,
        self_type: type | None = None,
        config: TypeCheckConfiguration = global_config,
    ):
        self.globals = globals
        # Instrumentation injects imports (such as TypeCheckMemo itself and the
        # check functions) into instrumented functions, so those names end up
        # in the locals snapshot. They must not shadow the function's own
        # globals when forward references are resolved against these locals,
        # so entries pointing at typeguard's own internals are dropped.
        self.locals = {
            key: value
            for key, value in locals.items()
            if not _is_typeguard_internal(value)
        }
        self.self_type = self_type
        self.config = config
