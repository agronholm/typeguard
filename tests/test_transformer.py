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
            _call_memo = CallMemo(foo, locals(), has_self_arg=False, \
unwrap_generator_annotations=True)
            check_argument_types(_call_memo)
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
            _call_memo = CallMemo(foo, locals(), has_self_arg=False, \
unwrap_generator_annotations=True)
            return check_return_type(6, _call_memo)
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
            _call_memo = check_argument_types = check_return_type = None

            def foo(x: int) -> int:
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

        _call_memo = CallMemo = check_argument_types = check_return_type = None

        def foo(x: int) -> None:
            _call_memo_ = CallMemo_(foo, locals(), has_self_arg=False, \
unwrap_generator_annotations=True)
            check_argument_types_(_call_memo_)
            return check_return_type_(x, _call_memo_)
        """
        ).strip()
    )


def test_avoid_local_names() -> None:
    node = parse(
        dedent(
            """
            def foo(x: int) -> int:
                _call_memo = check_argument_types = check_return_type = None
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
            _call_memo_ = CallMemo_(foo, locals(), has_self_arg=False, \
unwrap_generator_annotations=True)
            check_argument_types_(_call_memo_)
            _call_memo = CallMemo = check_argument_types = check_return_type = None
            return check_return_type_(x, _call_memo_)
        """
        ).strip()
    )
