import sys
from ast import parse
from textwrap import dedent

import pytest

from typeguard._transformer import TypeguardTransformer

if sys.version_info >= (3, 9):
    from ast import unparse
else:
    pytest.skip("Requires Python 3.9 or newer", allow_module_level=True)

todo = pytest.mark.xfail(reason="To be improved in the future")


def test_arguments_only() -> None:
    node = parse(
        dedent(
            """
            def foo(x: int) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard._functions import CallMemo, check_argument_types

            def foo(x: int) -> None:
                call_memo = CallMemo(foo, locals())
                check_argument_types(call_memo)
        """
        ).strip()
    )


def test_return_only() -> None:
    node = parse(
        dedent(
            """
            def foo(x) -> int:
                return 6
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard._functions import CallMemo, check_return_type

            def foo(x) -> int:
                call_memo = CallMemo(foo, locals())
                return check_return_type(6, call_memo)
        """
        ).strip()
    )


class TestGenerator:
    def test_yield(self) -> None:
        node = parse(
            dedent(
                """
                from collections.abc import Generator

                def foo(x) -> Generator[int, Any, str]:
                    yield 2
                    yield 6
                    return 'test'
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_return_type, \
check_send_type, check_yield_type
                from collections.abc import Generator

                def foo(x) -> Generator[int, Any, str]:
                    call_memo = CallMemo(foo, locals())
                    check_send_type((yield check_yield_type(2, call_memo)), call_memo)
                    check_send_type((yield check_yield_type(6, call_memo)), call_memo)
                    return check_return_type('test', call_memo)
            """
            ).strip()
        )

    @todo
    def test_no_return_type_check(self) -> None:
        node = parse(
            dedent(
                """
                from collections.abc import Generator

                def foo(x) -> Generator[int, None, None]:
                    yield 2
                    yield 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_send_type, \
check_yield_type
                from collections.abc import Generator

                def foo(x) -> Generator[int, None, None]:
                    call_memo = CallMemo(foo, locals())
                    check_send_type((yield check_yield_type(2, call_memo)), call_memo)
                    check_send_type((yield check_yield_type(6, call_memo)), call_memo)
            """
            ).strip()
        )

    @todo
    def test_no_send_type_check(self) -> None:
        node = parse(
            dedent(
                """
                from typing import Any
                from collections.abc import Generator

                def foo(x) -> Generator[int, Any, Any]:
                    yield 2
                    yield 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_yield_type
                from typing import Any
                from collections.abc import Generator

                def foo(x) -> Generator[int, Any, Any]:
                    call_memo = CallMemo(foo, locals())
                    yield check_yield_type(2, call_memo)
                    yield check_yield_type(6, call_memo)
            """
            ).strip()
        )


class TestAsyncGenerator:
    def test_full(self) -> None:
        node = parse(
            dedent(
                """
                from collections.abc import AsyncGenerator

                async def foo(x) -> AsyncGenerator[int, None]:
                    yield 2
                    yield 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_send_type, \
check_yield_type
                from collections.abc import AsyncGenerator

                async def foo(x) -> AsyncGenerator[int, None]:
                    call_memo = CallMemo(foo, locals())
                    check_send_type((yield check_yield_type(2, call_memo)), call_memo)
                    check_send_type((yield check_yield_type(6, call_memo)), call_memo)
            """
            ).strip()
        )

    @todo
    def test_no_yield_type_check(self) -> None:
        node = parse(
            dedent(
                """
                from typing import Any
                from collections.abc import AsyncGenerator

                async def foo() -> AsyncGenerator[Any, None]:
                    yield 2
                    yield 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_send_type
                from typing import Any
                from collections.abc import AsyncGenerator

                async def foo() -> AsyncGenerator[Any, None]:
                    call_memo = CallMemo(foo, locals())
                    check_send_type(yield 2, call_memo)
                    check_send_type(yield 6, call_memo)
                """
            ).strip()
        )

    @todo
    def test_no_send_type_check(self) -> None:
        node = parse(
            dedent(
                """
                from typing import Any
                from collections.abc import AsyncGenerator

                async def foo() -> AsyncGenerator[int, Any]:
                    yield 2
                    yield 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_send_type, \
check_yield_type
                from typing import Any
                from collections.abc import AsyncGenerator

                async def foo() -> AsyncGenerator[int, Any]:
                    call_memo = CallMemo(foo, locals())
                    yield check_yield_type(2, call_memo)
                    yield check_yield_type(6, call_memo)
                """
            ).strip()
        )


def test_pass_only() -> None:
    node = parse(
        dedent(
            """
            def foo(x) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            def foo(x) -> None:
                pass
            """
        ).strip()
    )


@pytest.mark.parametrize(
    "import_line, decorator",
    [
        pytest.param("from typing import no_type_check", "@no_type_check"),
        pytest.param("from typeguard import typeguard_ignore", "@typeguard_ignore"),
        pytest.param("import typing", "@typing.no_type_check"),
        pytest.param("import typeguard", "@typeguard.typeguard_ignore"),
    ],
)
def test_no_type_check_decorator(import_line: str, decorator: str) -> None:
    node = parse(
        dedent(
            f"""
            {import_line}

            {decorator}
            def foo(x: int) -> int:
                return x
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            f"""
            {import_line}

            {decorator}
            def foo(x: int) -> int:
                return x
        """
        ).strip()
    )


@pytest.mark.parametrize(
    "import_line, annotation",
    [
        pytest.param("from typing import Any", "Any"),
        pytest.param("from typing import Any as AlterAny", "AlterAny"),
        pytest.param("from typing_extensions import Any", "Any"),
        pytest.param("from typing_extensions import Any as AlterAny", "AlterAny"),
        pytest.param("import typing", "typing.Any"),
        pytest.param("import typing as typing_alter", "typing_alter.Any"),
        pytest.param("import typing_extensions as typing_alter", "typing_alter.Any"),
    ],
)
def test_any_only(import_line: str, annotation: str) -> None:
    node = parse(
        dedent(
            f"""
            {import_line}

            def foo(x, y: {annotation}) -> {annotation}:
                return 1
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            f"""
            {import_line}

            def foo(x, y: {annotation}) -> {annotation}:
                return 1
            """
        ).strip()
    )


def test_avoid_global_names() -> None:
    node = parse(
        dedent(
            """
            call_memo = CallMemo = check_argument_types = check_return_type = None

            def foo(x: int) -> int:
                dummy = (call_memo,)
                return x
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard._functions import CallMemo as CallMemo_, \
check_argument_types as check_argument_types_, check_return_type as check_return_type_
            call_memo = CallMemo = check_argument_types = check_return_type = None

            def foo(x: int) -> int:
                call_memo_ = CallMemo_(foo, locals())
                check_argument_types_(call_memo_)
                dummy = (call_memo,)
                return check_return_type_(x, call_memo_)
        """
        ).strip()
    )


def test_avoid_local_names() -> None:
    node = parse(
        dedent(
            """
            def foo(x: int) -> int:
                call_memo = CallMemo = check_argument_types = check_return_type = None
                return x
            """
        )
    )
    TypeguardTransformer(["foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            def foo(x: int) -> int:
                from typeguard._functions import CallMemo as CallMemo_, \
check_argument_types as check_argument_types_, check_return_type as check_return_type_
                call_memo_ = CallMemo_(foo, locals())
                check_argument_types_(call_memo_)
                call_memo = CallMemo = check_argument_types = check_return_type = None
                return check_return_type_(x, call_memo_)
            """
        ).strip()
    )


def test_method() -> None:
    node = parse(
        dedent(
            """
            class Foo:
                def foo(self, x: int) -> int:
                    return x
            """
        )
    )
    TypeguardTransformer(["Foo", "foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            class Foo:

                def foo(self, x: int) -> int:
                    from typeguard._functions import CallMemo, check_argument_types, \
check_return_type
                    call_memo = CallMemo(Foo.foo, locals(), self.__class__)
                    check_argument_types(call_memo)
                    return check_return_type(x, call_memo)
            """
        ).strip()
    )


def test_classmethod() -> None:
    node = parse(
        dedent(
            """
            class Foo:
                @classmethod
                def foo(cls, x: int) -> int:
                    return x
            """
        )
    )
    TypeguardTransformer(["Foo", "foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            class Foo:

                @classmethod
                def foo(cls, x: int) -> int:
                    from typeguard._functions import CallMemo, check_argument_types, \
check_return_type
                    call_memo = CallMemo(Foo.foo, locals(), cls)
                    check_argument_types(call_memo)
                    return check_return_type(x, call_memo)
            """
        ).strip()
    )


def test_staticmethod() -> None:
    node = parse(
        dedent(
            """
            class Foo:
                @staticmethod
                def foo(x: int) -> int:
                    return x
            """
        )
    )
    TypeguardTransformer(["Foo", "foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            class Foo:

                @staticmethod
                def foo(x: int) -> int:
                    from typeguard._functions import CallMemo, check_argument_types, \
check_return_type
                    call_memo = CallMemo(Foo.foo, locals())
                    check_argument_types(call_memo)
                    return check_return_type(x, call_memo)
            """
        ).strip()
    )


def test_local_function() -> None:
    node = parse(
        dedent(
            """
            def wrapper():
                def foo(x: int) -> int:
                    return x

                def foo2(x: int) -> int:
                    return x

                return foo
            """
        )
    )
    TypeguardTransformer(["wrapper", "foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            def wrapper():

                def foo(x: int) -> int:
                    from typeguard._functions import CallMemo, check_argument_types, \
check_return_type
                    call_memo = CallMemo(foo, locals())
                    check_argument_types(call_memo)
                    return check_return_type(x, call_memo)

                def foo2(x: int) -> int:
                    return x
                return foo
            """
        ).strip()
    )


def test_function_local_class_method() -> None:
    node = parse(
        dedent(
            """
            def wrapper():

                class Foo:

                    class Bar:

                        def method(self, x: int) -> int:
                            return x

                        def method2(self, x: int) -> int:
                            return x
            """
        )
    )
    TypeguardTransformer(["wrapper", "Foo", "Bar", "method"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            def wrapper():

                class Foo:

                    class Bar:

                        def method(self, x: int) -> int:
                            from typeguard._functions import CallMemo, \
check_argument_types, check_return_type
                            call_memo = CallMemo(method, locals(), self.__class__)
                            check_argument_types(call_memo)
                            return check_return_type(x, call_memo)

                        def method2(self, x: int) -> int:
                            return x
            """
        ).strip()
    )


class TestAssign:
    def test_annotated_assign(self) -> None:
        node = parse(
            dedent(
                """
                def foo() -> None:
                    x: int = otherfunc()
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_variable_assignment

                def foo() -> None:
                    call_memo = CallMemo(foo, locals())
                    x: int = check_variable_assignment(otherfunc(), {'x': int}, \
call_memo)
                """
            ).strip()
        )

    def test_multi_assign(self) -> None:
        node = parse(
            dedent(
                """
                def foo() -> None:
                    x: int
                    z: bytes
                    x, y, z = otherfunc()
                """
            )
        )
        TypeguardTransformer().visit(node)
        target = "x, y, z" if sys.version_info >= (3, 11) else "(x, y, z)"
        assert (
            unparse(node)
            == dedent(
                f"""
                from typeguard._functions import CallMemo, check_variable_assignment

                def foo() -> None:
                    call_memo = CallMemo(foo, locals())
                    x: int
                    z: bytes
                    {target} = check_variable_assignment(otherfunc(), \
{{'x': int, 'z': bytes}}, call_memo)
                """
            ).strip()
        )

    def test_assignment_annotated_argument(self) -> None:
        node = parse(
            dedent(
                """
                def foo(x: int) -> None:
                    x = 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_argument_types, \
check_variable_assignment

                def foo(x: int) -> None:
                    call_memo = CallMemo(foo, locals())
                    check_argument_types(call_memo)
                    x = check_variable_assignment(6, {'x': int}, call_memo)
                """
            ).strip()
        )

    def test_assignment_expr(self) -> None:
        node = parse(
            dedent(
                """
                def foo() -> None:
                    x: int
                    if x := otherfunc():
                        pass
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_variable_assignment

                def foo() -> None:
                    call_memo = CallMemo(foo, locals())
                    x: int
                    if (x := check_variable_assignment(otherfunc(), {'x': int}, \
call_memo)):
                        pass
                """
            ).strip()
        )

    def test_assignment_expr_annotated_argument(self) -> None:
        node = parse(
            dedent(
                """
                def foo(x: int) -> None:
                    if x := otherfunc():
                        pass
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_argument_types, \
check_variable_assignment

                def foo(x: int) -> None:
                    call_memo = CallMemo(foo, locals())
                    check_argument_types(call_memo)
                    if (x := check_variable_assignment(otherfunc(), {'x': int}, \
call_memo)):
                        pass
                """
            ).strip()
        )

    @pytest.mark.parametrize(
        "operator, function",
        [
            pytest.param("+=", "__iadd__", id="add"),
            pytest.param("-=", "__isub__", id="subtract"),
            pytest.param("*=", "__imul__", id="multiply"),
            pytest.param("@=", "__imatmul__", id="matrix_multiply"),
            pytest.param("/=", "__itruediv__", id="div"),
            pytest.param("//=", "__ifloordiv__", id="floordiv"),
            pytest.param("**=", "__ipow__", id="power"),
            pytest.param("<<=", "__ilshift__", id="left_bitshift"),
            pytest.param(">>=", "__irshift__", id="right_bitshift"),
            pytest.param("&=", "__iand__", id="and"),
            pytest.param("^=", "__ixor__", id="xor"),
            pytest.param("|=", "__ior__", id="or"),
        ],
    )
    def test_augmented_assignment(self, operator: str, function: str) -> None:
        node = parse(
            dedent(
                f"""
                def foo() -> None:
                    x: int
                    x {operator} 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                f"""
                from typeguard._functions import CallMemo, check_variable_assignment

                def foo() -> None:
                    call_memo = CallMemo(foo, locals())
                    x: int
                    x = check_variable_assignment(x.{function}(6), {{'x': int}}, \
call_memo)
                """
            ).strip()
        )

    def test_augmented_assignment_non_annotated(self) -> None:
        node = parse(
            dedent(
                """
                def foo() -> None:
                    x = 1
                    x += 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                def foo() -> None:
                    x = 1
                    x += 6
                """
            ).strip()
        )

    def test_augmented_assignment_annotated_argument(self) -> None:
        node = parse(
            dedent(
                """
                def foo(x: int) -> None:
                    x += 6
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard._functions import CallMemo, check_argument_types, \
check_variable_assignment

                def foo(x: int) -> None:
                    call_memo = CallMemo(foo, locals())
                    check_argument_types(call_memo)
                    x = check_variable_assignment(x.__iadd__(6), {'x': int}, call_memo)
                """
            ).strip()
        )
