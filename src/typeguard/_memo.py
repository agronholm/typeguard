from __future__ import annotations

from typing import Any

from typeguard._config import TypeCheckConfiguration, global_config


def _is_typeguard_internal(value: Any) -> bool:
    module: str = getattr(value, "__module__", None) or ""
    return module == "typeguard" or module.startswith("typeguard.")


# Names instrumentation injects whose values are typeguard's own internals.
# Only entries under one of these names can ever need dropping from the
# locals snapshot: the other injected imports come from other modules
# (dataclasses.replace, typing.Any, operator helpers) and the value filter
# would keep them anyway. Aliases gain one "_" per collision, so a few
# suffix depths are checked; a deeper alias can only arise from just as many
# colliding user bindings, in which case one of the checked names is present
# and the full scan below still runs. The candidate keys are precomputed so
# the check costs a few dict lookups and no string building per call.
_INJECTED_INTERNAL_KEYS: frozenset[str] = frozenset(
    f"{name}{'_' * suffix}"
    for name in (
        "TypeCheckMemo",
        "check_argument_types_internal",
        "check_return_type_internal",
        "check_yield_type",
        "check_send_type",
        "check_variable_assignment",
        "global_config",
    )
    for suffix in range(4)
)


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
        # Scanning every value costs a getattr per entry on every call, which
        # dominates a module-level check_type() loop over hundreds of globals,
        # so only do it when an injected name (or an aliased variant of one)
        # is actually present: otherwise a plain copy preserves the snapshot
        # semantics with no per-value work.
        # (Iterate over the small candidate set, not the locals dict:
        # isdisjoint() would walk all of locals instead.)
        if not any(key in locals for key in _INJECTED_INTERNAL_KEYS):
            self.locals = dict(locals)
        else:
            self.locals = {
                key: value
                for key, value in locals.items()
                if not _is_typeguard_internal(value)
            }
        self.self_type = self_type
        self.config = config
