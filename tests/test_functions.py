from typing import Any

import pytest
from pytest import raises

from typeguard import (
    TypeCheckError,
    TypeCheckMemo,
    check_argument_types,
    check_return_type,
    typechecked,
)


class TestCheckArgumentTypes:
    def test_success(self) -> None:
        def foo(x: int, /, y: str, *args: bool, z: bytes, **kwargs: int) -> None:
            check_argument_types()

        foo(1, "foo", True, False, z=b"foo", xyz=657, zzz=111)

    @pytest.mark.parametrize(
        "args, kwargs, pattern",
        [
            pytest.param(
                ("bar", "foo"),
                {"z": b"foo"},
                r'argument "x" \(str\) is not an instance of int',
                id="posonlyarg",
            ),
            pytest.param(
                (1, 1),
                {"z": b"foo"},
                r'argument "y" \(int\) is not an instance of str',
                id="posarg",
            ),
            pytest.param(
                (1, "foo"),
                {"z": "foo"},
                r'argument "z" \(str\) is not bytes-like',
                id="kwonlyarg",
            ),
            pytest.param(
                (1, "foo", 2),
                {"z": b"foo"},
                r'item 0 of argument "args" \(tuple\) is not an instance of bool',
                id="vararg",
            ),
            pytest.param(
                (1, "foo"),
                {"z": b"foo", "xyz": b"foo"},
                r"value of key 'xyz' of argument \"kwargs\" \(dict\) is not an instance of int",
                id="varkwarg",
            ),
        ],
    )
    def test_failure(
        self, args: tuple[Any], kwargs: dict[str, Any], pattern: str
    ) -> None:
        def foo(x: int, /, y: str, *args: bool, z: bytes, **kwargs: int) -> None:
            check_argument_types()

        with raises(TypeCheckError, match=pattern):
            foo(*args, **kwargs)


class TestCheckReturnType:
    def test_success(self) -> None:
        def foo() -> int:
            return check_return_type(0)

        foo()

    def test_no_return_annotation(self) -> None:
        def foo():
            return check_return_type(0)

        assert foo() == 0

    def test_none_return_annotation(self) -> None:
        def foo() -> None:
            return check_return_type(0)

        with raises(
            TypeCheckError,
            match=r"the return value \(int\) is not an instance of NoneType",
        ):
            foo()

    def test_failure(self) -> None:
        def foo() -> int:
            return check_return_type("foo")

        with raises(
            TypeCheckError, match=r"the return value \(str\) is not an instance of int"
        ):
            foo()


class TestTypeCheckMemo:
    def test_locals_without_injected_names_are_kept(self) -> None:
        # Regression test for #618: with no injected name present, the
        # locals snapshot is a plain copy (no per-value scan), so a
        # module-level check_type() loop over hundreds of globals stays
        # cheap while the snapshot semantics are preserved.
        locals_dict = {f"var{i}": i for i in range(400)}
        memo = TypeCheckMemo(locals_dict, locals_dict)
        assert memo.locals == locals_dict
        assert memo.locals is not locals_dict

    def test_injected_names_are_dropped(self) -> None:
        # The injected names (and their underscore-suffixed aliases) must
        # not shadow the function's own globals when forward references are
        # resolved against these locals.
        locals_dict = {
            "x": 1,
            "TypeCheckMemo": TypeCheckMemo,
            "TypeCheckMemo_": TypeCheckMemo,
            "check_argument_types_internal": check_argument_types,
        }
        memo = TypeCheckMemo(locals_dict, locals_dict)
        assert memo.locals == {"x": 1}

    def test_user_typeguard_objects_are_kept(self) -> None:
        # Only the injected names are dropped: a user-owned typeguard object
        # under its own name stays in the snapshot (it resolves to the same
        # object either way, and keeping it matches Python scoping).
        locals_dict = {"typechecked": typechecked, "x": 1}
        memo = TypeCheckMemo(locals_dict, locals_dict)
        assert memo.locals == locals_dict
