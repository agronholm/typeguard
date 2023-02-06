import sys
from ast import parse
from textwrap import dedent

from typeguard._transformer import TypeguardTransformer

if sys.version_info >= (3, 9):
    from ast import unparse
else:
    from astunparse import unparse


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
        from typeguard import CallMemo, check_argument_types

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
        from typeguard import CallMemo, check_return_type

        def foo(x) -> int:
            call_memo = CallMemo(foo, locals())
            return check_return_type(6, call_memo)
        """
        ).strip()
    )


def test_yield() -> None:
    node = parse(
        dedent(
            """
            from collections.abc import Generator

            def foo(x) -> Generator[int, Any, None]:
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
            from typeguard import CallMemo, check_return_type, check_send_type, \
check_yield_type
            from collections.abc import Generator

            def foo(x) -> Generator[int, Any, None]:
                call_memo = CallMemo(foo, locals())
                check_send_type((yield check_yield_type(2, call_memo)), call_memo)
                check_send_type((yield check_yield_type(6, call_memo)), call_memo)
                return check_return_type(None, call_memo)
        """
        ).strip()
    )


def test_async_yield() -> None:
    node = parse(
        dedent(
            """
            from collections.abc import AsyncGenerator

            async def foo(x) -> AsyncGenerator[int, Any]:
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
            from typeguard import CallMemo, check_send_type, check_yield_type
            from collections.abc import AsyncGenerator

            async def foo(x) -> AsyncGenerator[int, Any]:
                call_memo = CallMemo(foo, locals())
                check_send_type((yield check_yield_type(2, call_memo)), call_memo)
                check_send_type((yield check_yield_type(6, call_memo)), call_memo)
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


def test_no_instrumentation() -> None:
    node = parse(
        dedent(
            """
            from typing import Any

            def foo(x, y: Any) -> Any:
                return 1
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
        from typing import Any

        def foo(x, y: Any) -> Any:
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
            from typeguard import CallMemo as CallMemo_, check_argument_types as \
check_argument_types_, check_return_type as check_return_type_
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
                from typeguard import CallMemo as CallMemo_, check_argument_types as \
check_argument_types_, check_return_type as check_return_type_
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
                    from typeguard import CallMemo, check_argument_types, \
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
                    from typeguard import CallMemo, check_argument_types, \
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
                    from typeguard import CallMemo, check_argument_types, \
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
                    from typeguard import CallMemo, check_argument_types, \
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
                            from typeguard import CallMemo, check_argument_types, \
check_return_type
                            call_memo = CallMemo(method, locals(), self.__class__)
                            check_argument_types(call_memo)
                            return check_return_type(x, call_memo)

                        def method2(self, x: int) -> int:
                            return x
            """
        ).strip()
    )
