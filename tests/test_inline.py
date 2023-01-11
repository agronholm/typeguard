import sys
import traceback
from typing import Callable, NoReturn

import pytest

from typeguard import TypeCheckError, check_argument_types, check_return_type

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


class TestCheckArgumentTypes:
    def test_valid(self):
        def foo(a: str, b: int) -> None:
            assert check_argument_types()

        foo("bar", 5)

    def test_invalid(self):
        def foo(a: str, b: int) -> None:
            assert check_argument_types()

        pytest.raises(TypeCheckError, foo, "bar", "bah").match(
            'argument "b" is not an instance of int'
        )

    def test_short_tracebacks(self):
        def foo(a: Callable[..., int]):
            assert check_argument_types()

        try:
            foo(1)
        except TypeCheckError:
            _, _, tb = sys.exc_info()
            parts = traceback.extract_tb(tb)
            typeguard_lines = [
                part
                for part in parts
                if part.filename.endswith("typeguard/__init__.py")
            ]
            assert len(typeguard_lines) == 1

    def test_annotated_valid(self):
        def foo(a: Annotated[str, "foo"]):
            assert check_argument_types()

        foo("blah")

    def test_annotated_fail(self):
        def foo(a: Annotated[str, "foo"]):
            assert check_argument_types()

        pytest.raises(TypeCheckError, foo, 1).match('"a" is not an instance of str')

    def test_varargs_success(self):
        def foo(*args: str) -> None:
            assert check_argument_types()

        foo("bar")

    def test_varargs_fail(self):
        def foo(*args: str) -> None:
            assert check_argument_types()

        pytest.raises(TypeCheckError, foo, 1).match(
            'item 0 of argument "args" is not an instance of str'
        )

    def test_varkwargs_success(self):
        def foo(**kwargs: str) -> None:
            assert check_argument_types()

        foo(a="foo")

    def test_varkwargs_fail(self):
        def foo(**kwargs: str) -> None:
            assert check_argument_types()

        pytest.raises(TypeCheckError, foo, bar=1).match(
            "value of key 'bar' of argument \"kwargs\" is not an instance of str"
        )


class TestCheckReturnType:
    def test_valid(self):
        def foo() -> str:
            assert check_return_type("bah")
            return "bah"

        foo()

    def test_invalid(self):
        def foo() -> int:
            assert check_return_type("bah")
            return "bah"

        pytest.raises(TypeCheckError, foo).match(
            "the return value is not an instance of int"
        )

    def test_noreturn(self):
        def foo() -> NoReturn:
            assert check_return_type("bah")

        pytest.raises(TypeCheckError, foo).match(
            r"tests.test_inline.TestCheckReturnType.test_noreturn.<locals>.foo\(\) was "
            r"declared never to return but it did"
        )

    def test_notimplemented_valid(self):
        class Foo:
            def __eq__(self, other) -> bool:
                assert check_return_type(NotImplemented)
                return NotImplemented

        assert Foo().__eq__(1) is NotImplemented

    def test_notimplemented_invalid(self):
        def foo() -> bool:
            assert check_return_type(NotImplemented)
            return NotImplemented

        pytest.raises(TypeCheckError, foo).match(
            "the return value is not an instance of bool"
        )
