import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from pytest import raises

from typeguard import TypeCheckError, check_argument_types, check_return_type


@pytest.fixture(scope="module")
def deferredmanual() -> ModuleType:
    # Import a real module that uses ``from __future__ import annotations`` (PEP 563)
    this_dir = str(Path(__file__).parent)
    sys.path.insert(0, this_dir)
    try:
        return import_module("deferredmanual")
    finally:
        sys.path.remove(this_dir)


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

    def test_future_annotations_success(self, deferredmanual: ModuleType) -> None:
        deferredmanual.foo(1, "foo", True, False, z=b"foo", xyz=657, zzz=111)

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
    def test_future_annotations_failure(
        self,
        deferredmanual: ModuleType,
        args: tuple[Any],
        kwargs: dict[str, Any],
        pattern: str,
    ) -> None:
        # The same checks must apply when the calling module uses
        # ``from __future__ import annotations`` and the annotations are thus
        # plain strings
        with raises(TypeCheckError, match=pattern):
            deferredmanual.foo(*args, **kwargs)


class TestCheckReturnType:
    def test_success(self) -> None:
        def foo() -> int:
            return check_return_type(0)

        foo()

    def test_failure(self) -> None:
        def foo() -> int:
            return check_return_type("foo")

        with raises(
            TypeCheckError, match=r"the return value \(str\) is not an instance of int"
        ):
            foo()
