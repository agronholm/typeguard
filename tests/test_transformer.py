import sys
from ast import parse
from textwrap import dedent

import pytest

from typeguard._transformer import TypeguardTransformer

if sys.version_info >= (3, 9):
    from ast import unparse
else:
    pytest.skip("Requires Python 3.9 or newer", allow_module_level=True)


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
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types

            def foo(x: int) -> None:
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, int)}, memo)
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
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_return_type

            def foo(x) -> int:
                memo = TypeCheckMemo(globals(), locals())
                return check_return_type('foo', 6, int, memo)
        """
        ).strip()
    )


class TestGenerator:
    def test_yield(self) -> None:
        node = parse(
            dedent(
                """
                from collections.abc import Generator
                from typing import Any

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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_return_type, check_yield_type
                from collections.abc import Generator
                from typing import Any

                def foo(x) -> Generator[int, Any, str]:
                    memo = TypeCheckMemo(globals(), locals())
                    yield check_yield_type('foo', 2, int, memo)
                    yield check_yield_type('foo', 6, int, memo)
                    return check_return_type('foo', 'test', str, memo)
            """
            ).strip()
        )

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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_send_type, check_yield_type
                from collections.abc import Generator

                def foo(x) -> Generator[int, None, None]:
                    memo = TypeCheckMemo(globals(), locals())
                    check_send_type('foo', (yield check_yield_type('foo', 2, int, \
memo)), None, memo)
                    check_send_type('foo', (yield check_yield_type('foo', 6, int, \
memo)), None, memo)
            """
            ).strip()
        )

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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_yield_type
                from typing import Any
                from collections.abc import Generator

                def foo(x) -> Generator[int, Any, Any]:
                    memo = TypeCheckMemo(globals(), locals())
                    yield check_yield_type('foo', 2, int, memo)
                    yield check_yield_type('foo', 6, int, memo)
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_send_type, check_yield_type
                from collections.abc import AsyncGenerator

                async def foo(x) -> AsyncGenerator[int, None]:
                    memo = TypeCheckMemo(globals(), locals())
                    check_send_type('foo', (yield check_yield_type('foo', 2, int, \
memo)), None, memo)
                    check_send_type('foo', (yield check_yield_type('foo', 6, int, \
memo)), None, memo)
            """
            ).strip()
        )

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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_send_type
                from typing import Any
                from collections.abc import AsyncGenerator

                async def foo() -> AsyncGenerator[Any, None]:
                    memo = TypeCheckMemo(globals(), locals())
                    check_send_type('foo', (yield 2), None, memo)
                    check_send_type('foo', (yield 6), None, memo)
                """
            ).strip()
        )

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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_yield_type
                from typing import Any
                from collections.abc import AsyncGenerator

                async def foo() -> AsyncGenerator[int, Any]:
                    memo = TypeCheckMemo(globals(), locals())
                    yield check_yield_type('foo', 2, int, memo)
                    yield check_yield_type('foo', 6, int, memo)
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


def test_any_in_union() -> None:
    node = parse(
        dedent(
            """
            from typing import Any, Union

            def foo(x, y: Union[Any, None]) -> Union[Any, None]:
                return 1
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typing import Any, Union

            def foo(x, y: Union[Any, None]) -> Union[Any, None]:
                return 1
            """
        ).strip()
    )


def test_any_in_pep_604_union() -> None:
    node = parse(
        dedent(
            """
            from typing import Any

            def foo(x, y: Any | None) -> Any | None:
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

            def foo(x, y: Any | None) -> Any | None:
                return 1
            """
        ).strip()
    )


def test_any_in_nested_dict() -> None:
    # Regression test for #373
    node = parse(
        dedent(
            """
            from typing import Any

            def foo(x: dict[str, dict[str, Any]]) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types
            from typing import Any

            def foo(x: dict[str, dict[str, Any]]) -> None:
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, dict[str, dict[str, Any]])}, memo)
            """
        ).strip()
    )


def test_avoid_global_names() -> None:
    node = parse(
        dedent(
            """
            memo = TypeCheckMemo = check_argument_types = check_return_type = None

            def func1(x: int) -> int:
                dummy = (memo,)
                return x

            def func2(x: int) -> int:
                return x
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo as TypeCheckMemo_
            from typeguard._functions import \
check_argument_types as check_argument_types_, check_return_type as check_return_type_
            memo = TypeCheckMemo = check_argument_types = check_return_type = None

            def func1(x: int) -> int:
                memo_ = TypeCheckMemo_(globals(), locals())
                check_argument_types_('func1', {'x': (x, int)}, memo_)
                dummy = (memo,)
                return check_return_type_('func1', x, int, memo_)

            def func2(x: int) -> int:
                memo_ = TypeCheckMemo_(globals(), locals())
                check_argument_types_('func2', {'x': (x, int)}, memo_)
                return check_return_type_('func2', x, int, memo_)
        """
        ).strip()
    )


def test_avoid_local_names() -> None:
    node = parse(
        dedent(
            """
            def foo(x: int) -> int:
                memo = TypeCheckMemo = check_argument_types = check_return_type = None
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
                from typeguard import TypeCheckMemo as TypeCheckMemo_
                from typeguard._functions import \
check_argument_types as check_argument_types_, check_return_type as check_return_type_
                memo_ = TypeCheckMemo_(globals(), locals())
                check_argument_types_('foo', {'x': (x, int)}, memo_)
                memo = TypeCheckMemo = check_argument_types = check_return_type = None
                return check_return_type_('foo', x, int, memo_)
            """
        ).strip()
    )


def test_avoid_nonlocal_names() -> None:
    node = parse(
        dedent(
            """
            def outer():
                memo = TypeCheckMemo = check_argument_types = check_return_type = None

                def foo(x: int) -> int:
                    return x

                return foo
            """
        )
    )
    TypeguardTransformer(["outer", "foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            def outer():
                memo = TypeCheckMemo = check_argument_types = check_return_type = None

                def foo(x: int) -> int:
                    from typeguard import TypeCheckMemo as TypeCheckMemo_
                    from typeguard._functions import \
check_argument_types as check_argument_types_, check_return_type as check_return_type_
                    memo_ = TypeCheckMemo_(globals(), locals())
                    check_argument_types_('outer.<locals>.foo', {'x': (x, int)}, memo_)
                    return check_return_type_('outer.<locals>.foo', x, int, memo_)
                return foo
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
                    from typeguard import TypeCheckMemo
                    from typeguard._functions import check_argument_types, \
check_return_type
                    memo = TypeCheckMemo(globals(), locals(), self_type=self.__class__)
                    check_argument_types('Foo.foo', {'x': (x, int)}, memo)
                    return check_return_type('Foo.foo', x, int, memo)
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
                    from typeguard import TypeCheckMemo
                    from typeguard._functions import check_argument_types, \
check_return_type
                    memo = TypeCheckMemo(globals(), locals(), self_type=cls)
                    check_argument_types('Foo.foo', {'x': (x, int)}, memo)
                    return check_return_type('Foo.foo', x, int, memo)
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
                    from typeguard import TypeCheckMemo
                    from typeguard._functions import check_argument_types, \
check_return_type
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('Foo.foo', {'x': (x, int)}, memo)
                    return check_return_type('Foo.foo', x, int, memo)
            """
        ).strip()
    )


def test_new_with_self() -> None:
    node = parse(
        dedent(
            """
            from typing import Self

            class Foo:
                def __new__(cls) -> Self:
                    return super().__new__(cls)
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_return_type
            from typing import Self

            class Foo:

                def __new__(cls) -> Self:
                    Foo = cls
                    memo = TypeCheckMemo(globals(), locals(), self_type=cls)
                    return check_return_type('Foo.__new__', super().__new__(cls), \
Self, memo)
            """
        ).strip()
    )


def test_new_with_explicit_class_name() -> None:
    # Regression test for #398
    node = parse(
        dedent(
            """
            class A:

                def __new__(cls) -> 'A':
                    return object.__new__(cls)
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_return_type

            class A:

                def __new__(cls) -> 'A':
                    A = cls
                    memo = TypeCheckMemo(globals(), locals(), self_type=cls)
                    return check_return_type('A.__new__', object.__new__(cls), A, memo)
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
                    from typeguard import TypeCheckMemo
                    from typeguard._functions import check_argument_types, \
check_return_type
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('wrapper.<locals>.foo', {'x': (x, int)}, memo)
                    return check_return_type('wrapper.<locals>.foo', x, int, memo)

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
                            from typeguard import TypeCheckMemo
                            from typeguard._functions import check_argument_types, \
check_return_type
                            memo = TypeCheckMemo(globals(), locals(), \
self_type=self.__class__)
                            check_argument_types('wrapper.<locals>.Foo.Bar.method', \
{'x': (x, int)}, memo)
                            return check_return_type(\
'wrapper.<locals>.Foo.Bar.method', x, int, memo)

                        def method2(self, x: int) -> int:
                            return x
            """
        ).strip()
    )


def test_keyword_only_argument() -> None:
    node = parse(
        dedent(
            """
            def foo(*, x: int) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types

            def foo(*, x: int) -> None:
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, int)}, memo)
            """
        ).strip()
    )


def test_positional_only_argument() -> None:
    node = parse(
        dedent(
            """
            def foo(x: int, /) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types

            def foo(x: int, /) -> None:
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, int)}, memo)
            """
        ).strip()
    )


def test_variable_positional_argument() -> None:
    node = parse(
        dedent(
            """
            def foo(*args: int) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types

            def foo(*args: int) -> None:
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'args': (args, tuple[int, ...])}, memo)
            """
        ).strip()
    )


def test_variable_keyword_argument() -> None:
    node = parse(
        dedent(
            """
            def foo(**kwargs: int) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types

            def foo(**kwargs: int) -> None:
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'kwargs': (kwargs, dict[str, int])}, memo)
            """
        ).strip()
    )


class TestTypecheckingImport:
    """
    Test that annotations imported conditionally on typing.TYPE_CHECKING are not used in
    run-time checks.
    """

    def test_direct_references(self) -> None:
        node = parse(
            dedent(
                """
                from typing import TYPE_CHECKING
                if TYPE_CHECKING:
                    import typing
                    from typing import Hashable, Sequence

                def foo(x: Hashable, y: typing.Collection, *args: Hashable, \
**kwargs: typing.Collection) -> Sequence:
                    bar: typing.Collection
                    baz: Hashable = 1
                    return (1, 2)
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typing import TYPE_CHECKING
                if TYPE_CHECKING:
                    import typing
                    from typing import Hashable, Sequence

                def foo(x: Hashable, y: typing.Collection, *args: Hashable, \
**kwargs: typing.Collection) -> Sequence:
                    bar: typing.Collection
                    baz: Hashable = 1
                    return (1, 2)
                """
            ).strip()
        )

    def test_collection_parameter(self) -> None:
        node = parse(
            dedent(
                """
                from typing import TYPE_CHECKING
                if TYPE_CHECKING:
                    from nonexistent import FooBar

                def foo(x: list[FooBar]) -> list[FooBar]:
                    return x
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types, check_return_type
                from typing import TYPE_CHECKING
                if TYPE_CHECKING:
                    from nonexistent import FooBar

                def foo(x: list[FooBar]) -> list[FooBar]:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {'x': (x, list)}, memo)
                    return check_return_type('foo', x, list, memo)
                """
            ).strip()
        )

    def test_variable_annotations(self) -> None:
        node = parse(
            dedent(
                """
                from typing import Any, TYPE_CHECKING
                if TYPE_CHECKING:
                    from nonexistent import FooBar

                def foo(x: Any) -> None:
                    y: FooBar = x
                    z: list[FooBar] = [y]
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_variable_assignment
                from typing import Any, TYPE_CHECKING
                if TYPE_CHECKING:
                    from nonexistent import FooBar

                def foo(x: Any) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    y: FooBar = x
                    z: list[FooBar] = check_variable_assignment([y], 'z', list, \
memo)
                """
            ).strip()
        )

    def test_generator_function(self) -> None:
        node = parse(
            dedent(
                """
                from typing import Any, TYPE_CHECKING
                from collections.abc import Generator
                if TYPE_CHECKING:
                    import typing
                    from typing import Hashable, Sequence

                def foo(x: Hashable, y: typing.Collection) -> Generator[Hashable, \
typing.Collection, Sequence]:
                    yield 'foo'
                    return (1, 2)
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typing import Any, TYPE_CHECKING
                from collections.abc import Generator
                if TYPE_CHECKING:
                    import typing
                    from typing import Hashable, Sequence

                def foo(x: Hashable, y: typing.Collection) -> Generator[Hashable, \
typing.Collection, Sequence]:
                    yield 'foo'
                    return (1, 2)
                """
            ).strip()
        )

    def test_optional(self) -> None:
        node = parse(
            dedent(
                """
                from typing import Any, Optional, TYPE_CHECKING
                if TYPE_CHECKING:
                    from typing import Hashable

                def foo(x: Optional[Hashable]) -> Optional[Hashable]:
                    return x
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typing import Any, Optional, TYPE_CHECKING
                if TYPE_CHECKING:
                    from typing import Hashable

                def foo(x: Optional[Hashable]) -> Optional[Hashable]:
                    return x
                """
            ).strip()
        )

    def test_optional_nested(self) -> None:
        node = parse(
            dedent(
                """
                from typing import Any, List, Optional

                def foo(x: List[Optional[int]]) -> None:
                    pass
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types
                from typing import Any, List, Optional

                def foo(x: List[Optional[int]]) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {'x': (x, List[Optional[int]])}, memo)
                """
            ).strip()
        )

    def test_subscript_within_union(self) -> None:
        # Regression test for #397
        node = parse(
            dedent(
                """
                from typing import Any, Iterable, Union, TYPE_CHECKING
                if TYPE_CHECKING:
                    from typing import Hashable

                def foo(x: Union[Iterable[Hashable], str]) -> None:
                    pass
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types
                from typing import Any, Iterable, Union, TYPE_CHECKING
                if TYPE_CHECKING:
                    from typing import Hashable

                def foo(x: Union[Iterable[Hashable], str]) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {'x': (x, Union[Iterable, str])}, memo)
                """
            ).strip()
        )

    def test_pep604_union(self) -> None:
        node = parse(
            dedent(
                """
                from typing import TYPE_CHECKING
                if TYPE_CHECKING:
                    from typing import Hashable

                def foo(x: Hashable | str) -> None:
                    pass
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typing import TYPE_CHECKING
                if TYPE_CHECKING:
                    from typing import Hashable

                def foo(x: Hashable | str) -> None:
                    pass
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_variable_assignment

                def foo() -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    x: int = check_variable_assignment(otherfunc(), 'x', int, memo)
                """
            ).strip()
        )

    def test_varargs_assign(self) -> None:
        node = parse(
            dedent(
                """
                def foo(*args: int) -> None:
                    args = (5,)
                """
            )
        )
        TypeguardTransformer().visit(node)

        if sys.version_info < (3, 9):
            extra_import = "from typing import Tuple\n"
            tuple_type = "Tuple"
        else:
            extra_import = ""
            tuple_type = "tuple"

        assert (
            unparse(node)
            == dedent(
                f"""
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types, \
check_variable_assignment
                {extra_import}
                def foo(*args: int) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {{'args': (args, \
{tuple_type}[int, ...])}}, memo)
                    args = check_variable_assignment((5,), 'args', \
{tuple_type}[int, ...], memo)
                """
            ).strip()
        )

    def test_kwargs_assign(self) -> None:
        node = parse(
            dedent(
                """
                def foo(**kwargs: int) -> None:
                    kwargs = {'a': 5}
                """
            )
        )
        TypeguardTransformer().visit(node)

        if sys.version_info < (3, 9):
            extra_import = "from typing import Dict\n"
            dict_type = "Dict"
        else:
            extra_import = ""
            dict_type = "dict"

        assert (
            unparse(node)
            == dedent(
                f"""
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types, \
check_variable_assignment
                {extra_import}
                def foo(**kwargs: int) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {{'kwargs': (kwargs, \
{dict_type}[str, int])}}, memo)
                    kwargs = check_variable_assignment({{'a': 5}}, 'kwargs', \
{dict_type}[str, int], memo)
                """
            ).strip()
        )

    @pytest.mark.skipif(sys.version_info >= (3, 10), reason="Requires Python < 3.10")
    def test_pep604_assign(self) -> None:
        node = parse(
            dedent(
                """
                Union = None

                def foo() -> None:
                    x: int | str = otherfunc()
                """
            )
        )
        TypeguardTransformer().visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_variable_assignment
                from typing import Union as Union_
                Union = None

                def foo() -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    x: int | str = check_variable_assignment(otherfunc(), 'x', \
Union_[int, str], memo)
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_multi_variable_assignment
                from typing import Any

                def foo() -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    x: int
                    z: bytes
                    {target} = check_multi_variable_assignment(otherfunc(), \
[{{'x': int, 'y': Any, 'z': bytes}}], memo)
                """
            ).strip()
        )

    def test_star_multi_assign(self) -> None:
        node = parse(
            dedent(
                """
                def foo() -> None:
                    x: int
                    z: bytes
                    x, *y, z = otherfunc()
                """
            )
        )
        TypeguardTransformer().visit(node)
        target = "x, *y, z" if sys.version_info >= (3, 11) else "(x, *y, z)"
        assert (
            unparse(node)
            == dedent(
                f"""
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_multi_variable_assignment
                from typing import Any

                def foo() -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    x: int
                    z: bytes
                    {target} = check_multi_variable_assignment(otherfunc(), \
[{{'x': int, '*y': Any, 'z': bytes}}], memo)
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types, \
check_variable_assignment

                def foo(x: int) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {'x': (x, int)}, memo)
                    x = check_variable_assignment(6, 'x', int, memo)
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_variable_assignment

                def foo() -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    x: int
                    if (x := check_variable_assignment(otherfunc(), 'x', int, \
memo)):
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types, \
check_variable_assignment

                def foo(x: int) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {'x': (x, int)}, memo)
                    if (x := check_variable_assignment(otherfunc(), 'x', int, memo)):
                        pass
                """
            ).strip()
        )

    @pytest.mark.parametrize(
        "operator, function",
        [
            pytest.param("+=", "iadd", id="add"),
            pytest.param("-=", "isub", id="subtract"),
            pytest.param("*=", "imul", id="multiply"),
            pytest.param("@=", "imatmul", id="matrix_multiply"),
            pytest.param("/=", "itruediv", id="div"),
            pytest.param("//=", "ifloordiv", id="floordiv"),
            pytest.param("**=", "ipow", id="power"),
            pytest.param("<<=", "ilshift", id="left_bitshift"),
            pytest.param(">>=", "irshift", id="right_bitshift"),
            pytest.param("&=", "iand", id="and"),
            pytest.param("^=", "ixor", id="xor"),
            pytest.param("|=", "ior", id="or"),
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_variable_assignment
                from operator import {function}

                def foo() -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    x: int
                    x = check_variable_assignment({function}(x, 6), 'x', int, memo)
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
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types, \
check_variable_assignment
                from operator import iadd

                def foo(x: int) -> None:
                    memo = TypeCheckMemo(globals(), locals())
                    check_argument_types('foo', {'x': (x, int)}, memo)
                    x = check_variable_assignment(iadd(x, 6), 'x', int, memo)
                """
            ).strip()
        )


def test_argname_typename_conflicts() -> None:
    node = parse(
        dedent(
            """
            from collections.abc import Generator

            def foo(x: kwargs, /, y: args, *args: x, baz: x, **kwargs: y) -> \
Generator[args, x, kwargs]:
                yield y
                return x
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from collections.abc import Generator

            def foo(x: kwargs, /, y: args, *args: x, baz: x, **kwargs: y) -> \
Generator[args, x, kwargs]:
                yield y
                return x
            """
        ).strip()
    )


def test_local_assignment_typename_conflicts() -> None:
    node = parse(
        dedent(
            """
            def foo() -> int:
                int = 6
                return int
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            def foo() -> int:
                int = 6
                return int
            """
        ).strip()
    )


def test_local_ann_assignment_typename_conflicts() -> None:
    node = parse(
        dedent(
            """
            from typing import Any

            def foo() -> int:
                int: Any = 6
                return int
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typing import Any

            def foo() -> int:
                int: Any = 6
                return int
            """
        ).strip()
    )


def test_local_named_expr_typename_conflicts() -> None:
    node = parse(
        dedent(
            """
            from typing import Any

            def foo() -> int:
                if (int := 6):
                    pass
                return int
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typing import Any

            def foo() -> int:
                if (int := 6):
                    pass
                return int
            """
        ).strip()
    )


def test_dont_leave_empty_ast_container_nodes() -> None:
    # Regression test for #352
    node = parse(
        dedent(
            """
            if True:

                class A:
                    ...

                def func():
                    ...

            def foo(x: str) -> None:
                pass
            """
        )
    )
    TypeguardTransformer(["foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            if True:
                pass

            def foo(x: str) -> None:
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, str)}, memo)
            """
        ).strip()
    )


def test_dont_leave_empty_ast_container_nodes_2() -> None:
    # Regression test for #352
    node = parse(
        dedent(
            """
            try:

                class A:
                    ...

                def func():
                    ...

            except:

                class A:
                    ...

                def func():
                    ...


            def foo(x: str) -> None:
                pass
            """
        )
    )
    TypeguardTransformer(["foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            try:
                pass
            except:
                pass

            def foo(x: str) -> None:
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, str)}, memo)
            """
        ).strip()
    )


class TestTypeShadowedByArgument:
    def test_typing_union(self) -> None:
        # Regression test for #394
        node = parse(
            dedent(
                """
                from __future__ import annotations
                from typing import Union

                class A:
                    ...

                def foo(A: Union[A, None]) -> None:
                    pass
                """
            )
        )
        TypeguardTransformer(["foo"]).visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from __future__ import annotations
                from typing import Union

                def foo(A: Union[A, None]) -> None:
                    pass
                """
            ).strip()
        )

    def test_pep604_union(self) -> None:
        # Regression test for #395
        node = parse(
            dedent(
                """
                from __future__ import annotations

                class A:
                    ...

                def foo(A: A | None) -> None:
                    pass
                """
            )
        )
        TypeguardTransformer(["foo"]).visit(node)
        assert (
            unparse(node)
            == dedent(
                """
                from __future__ import annotations

                def foo(A: A | None) -> None:
                    pass
                """
            ).strip()
        )


def test_dont_parse_annotated_2nd_arg() -> None:
    # Regression test for #352
    node = parse(
        dedent(
            """
            from typing import Annotated

            def foo(x: Annotated[str, 'foo bar']) -> None:
                pass
            """
        )
    )
    TypeguardTransformer(["foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typing import Annotated

            def foo(x: Annotated[str, 'foo bar']) -> None:
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_argument_types
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, Annotated[str, 'foo bar'])}, memo)
            """
        ).strip()
    )


def test_respect_docstring() -> None:
    # Regression test for #359
    node = parse(
        dedent(
            '''
            def foo() -> int:
                """This is a docstring."""
                return 1
            '''
        )
    )
    TypeguardTransformer(["foo"]).visit(node)
    assert (
        unparse(node)
        == dedent(
            '''
            def foo() -> int:
                """This is a docstring."""
                from typeguard import TypeCheckMemo
                from typeguard._functions import check_return_type
                memo = TypeCheckMemo(globals(), locals())
                return check_return_type('foo', 1, int, memo)
            '''
        ).strip()
    )


def test_respect_future_import() -> None:
    # Regression test for #385
    node = parse(
        dedent(
            '''
            """module docstring"""
            from __future__ import annotations

            def foo() -> int:
                return 1
            '''
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            '''
            """module docstring"""
            from __future__ import annotations
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_return_type

            def foo() -> int:
                memo = TypeCheckMemo(globals(), locals())
                return check_return_type('foo', 1, int, memo)
            '''
        ).strip()
    )


def test_literal() -> None:
    # Regression test for #399
    node = parse(
        dedent(
            """
            from typing import Literal

            def foo(x: Literal['a', 'b']) -> None:
                pass
            """
        )
    )
    TypeguardTransformer().visit(node)
    assert (
        unparse(node)
        == dedent(
            """
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types
            from typing import Literal

            def foo(x: Literal['a', 'b']) -> None:
                memo = TypeCheckMemo(globals(), locals())
                check_argument_types('foo', {'x': (x, Literal['a', 'b'])}, memo)
            """
        ).strip()
    )
