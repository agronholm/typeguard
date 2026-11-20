import asyncio
import subprocess
import sys
import warnings
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from textwrap import dedent
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterable,
    AsyncIterator,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
)
from unittest.mock import Mock

import pytest

from typeguard import (
    TypeCheckError,
    TypeHintWarning,
    install_import_hook,
    typechecked,
)

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


class TestCoroutineFunction:
    def test_success(self):
        @typechecked
        async def foo(a: int) -> str:
            return "test"

        assert asyncio.run(foo(1)) == "test"

    def test_bad_arg(self):
        @typechecked
        async def foo(a: int) -> str:
            return "test"

        with pytest.raises(
            TypeCheckError, match=r'argument "a" \(str\) is not an instance of int'
        ):
            asyncio.run(foo("foo"))

    def test_bad_return(self):
        @typechecked
        async def foo(a: int) -> str:
            return 1

        with pytest.raises(
            TypeCheckError, match=r"return value \(int\) is not an instance of str"
        ):
            asyncio.run(foo(1))

    def test_any_return(self):
        @typechecked
        async def foo() -> Any:
            return 1

        assert asyncio.run(foo()) == 1


class TestGenerator:
    def test_generator_bare(self):
        @typechecked
        def genfunc() -> Generator:
            val1 = yield 2
            val2 = yield 3
            val3 = yield 4
            return [val1, val2, val3]

        gen = genfunc()
        with pytest.raises(StopIteration) as exc:
            value = next(gen)
            while True:
                value = gen.send(str(value))
                assert isinstance(value, int)

        assert exc.value.value == ["2", "3", "4"]

    def test_generator_annotated(self):
        @typechecked
        def genfunc() -> Generator[int, str, List[str]]:
            val1 = yield 2
            val2 = yield 3
            val3 = yield 4
            return [val1, val2, val3]

        gen = genfunc()
        with pytest.raises(StopIteration) as exc:
            value = next(gen)
            while True:
                value = gen.send(str(value))
                assert isinstance(value, int)

        assert exc.value.value == ["2", "3", "4"]

    def test_generator_iterable_bare(self):
        @typechecked
        def genfunc() -> Iterable:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_generator_iterable_annotated(self):
        @typechecked
        def genfunc() -> Iterable[int]:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_generator_iterator_bare(self):
        @typechecked
        def genfunc() -> Iterator:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_generator_iterator_annotated(self):
        @typechecked
        def genfunc() -> Iterator[int]:
            yield 2
            yield 3
            yield 4

        values = list(genfunc())
        assert values == [2, 3, 4]

    def test_bad_yield_as_generator(self):
        @typechecked
        def genfunc() -> Generator[int, str, None]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen)

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_bad_yield_as_iterable(self):
        @typechecked
        def genfunc() -> Iterable[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen)

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_bad_yield_as_iterator(self):
        @typechecked
        def genfunc() -> Iterator[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen)

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_generator_bad_send(self):
        @typechecked
        def genfunc() -> Generator[int, str, None]:
            yield 1
            yield 2

        gen = genfunc()
        next(gen)
        with pytest.raises(TypeCheckError) as exc:
            gen.send(2)

        exc.match(r"value sent to generator \(int\) is not an instance of str")

    def test_generator_bad_return(self):
        @typechecked
        def genfunc() -> Generator[int, str, str]:
            yield 1
            return 6

        gen = genfunc()
        next(gen)
        with pytest.raises(TypeCheckError) as exc:
            gen.send("foo")

        exc.match(r"return value \(int\) is not an instance of str")

    def test_return_generator(self):
        @typechecked
        def genfunc() -> Generator[int, None, None]:
            yield 1

        @typechecked
        def foo() -> Generator[int, None, None]:
            return genfunc()

        foo()


class TestAsyncGenerator:
    def test_async_generator_bare(self):
        @typechecked
        async def genfunc() -> AsyncGenerator:
            values.append((yield 2))
            values.append((yield 3))
            values.append((yield 4))

        async def run_generator():
            gen = genfunc()
            value = await gen.asend(None)
            with pytest.raises(StopAsyncIteration):
                while True:
                    value = await gen.asend(str(value))
                    assert isinstance(value, int)

        values = []
        asyncio.run(run_generator())
        assert values == ["2", "3", "4"]

    def test_async_generator_annotated(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            values.append((yield 2))
            values.append((yield 3))
            values.append((yield 4))

        async def run_generator():
            gen = genfunc()
            value = await gen.asend(None)
            with pytest.raises(StopAsyncIteration):
                while True:
                    value = await gen.asend(str(value))
                    assert isinstance(value, int)

        values = []
        asyncio.run(run_generator())
        assert values == ["2", "3", "4"]

    def test_generator_iterable_bare(self):
        @typechecked
        async def genfunc() -> AsyncIterable:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_generator_iterable_annotated(self):
        @typechecked
        async def genfunc() -> AsyncIterable[int]:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_generator_iterator_bare(self):
        @typechecked
        async def genfunc() -> AsyncIterator:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_generator_iterator_annotated(self):
        @typechecked
        async def genfunc() -> AsyncIterator[int]:
            yield 2
            yield 3
            yield 4

        async def run_generator():
            return [value async for value in genfunc()]

        assert asyncio.run(run_generator()) == [2, 3, 4]

    def test_async_bad_yield_as_generator(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen.__anext__().__await__())

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_async_bad_yield_as_iterable(self):
        @typechecked
        async def genfunc() -> AsyncIterable[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen.__anext__().__await__())

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_async_bad_yield_as_iterator(self):
        @typechecked
        async def genfunc() -> AsyncIterator[int]:
            yield "foo"

        gen = genfunc()
        with pytest.raises(TypeCheckError) as exc:
            next(gen.__anext__().__await__())

        exc.match(r"the yielded value \(str\) is not an instance of int")

    def test_async_generator_bad_send(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, str]:
            yield 1
            yield 2

        gen = genfunc()
        pytest.raises(StopIteration, next, gen.__anext__().__await__())
        with pytest.raises(TypeCheckError) as exc:
            next(gen.asend(2).__await__())

        exc.match(r"the value sent to generator \(int\) is not an instance of str")

    def test_return_async_generator(self):
        @typechecked
        async def genfunc() -> AsyncGenerator[int, None]:
            yield 1

        @typechecked
        def foo() -> AsyncGenerator[int, None]:
            return genfunc()

        foo()

    def test_async_generator_iterate(self):
        @typechecked
        async def asyncgenfunc() -> AsyncGenerator[int, None]:
            yield 1

        asyncgen = asyncgenfunc()
        aiterator = asyncgen.__aiter__()
        exc = pytest.raises(StopIteration, aiterator.__anext__().send, None)
        assert exc.value.value == 1


class TestSelf:
    def test_return_valid(self):
        class Foo:
            @typechecked
            def method(self) -> Self:
                return self

        Foo().method()

    def test_return_invalid(self):
        class Foo:
            @typechecked
            def method(self) -> Self:
                return 1

        foo = Foo()
        pytest.raises(TypeCheckError, foo.method).match(
            rf"the return value \(int\) is not an instance of the self type "
            rf"\({__name__}\.{self.__class__.__name__}\.test_return_invalid\."
            rf"<locals>\.Foo\)"
        )

    def test_classmethod_return_valid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls) -> Self:
                return Foo()

        Foo.method()

    def test_classmethod_return_invalid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls) -> Self:
                return 1

        pytest.raises(TypeCheckError, Foo.method).match(
            rf"the return value \(int\) is not an instance of the self type "
            rf"\({__name__}\.{self.__class__.__name__}\."
            rf"test_classmethod_return_invalid\.<locals>\.Foo\)"
        )

    def test_arg_valid(self):
        class Foo:
            @typechecked
            def method(self, another: Self) -> None:
                pass

        foo = Foo()
        foo2 = Foo()
        foo.method(foo2)

    def test_arg_invalid(self):
        class Foo:
            @typechecked
            def method(self, another: Self) -> None:
                pass

        foo = Foo()
        pytest.raises(TypeCheckError, foo.method, 1).match(
            rf'argument "another" \(int\) is not an instance of the self type '
            rf"\({__name__}\.{self.__class__.__name__}\.test_arg_invalid\."
            rf"<locals>\.Foo\)"
        )

    def test_classmethod_arg_valid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls, another: Self) -> None:
                pass

        foo = Foo()
        Foo.method(foo)

    def test_classmethod_arg_invalid(self):
        class Foo:
            @classmethod
            @typechecked
            def method(cls, another: Self) -> None:
                pass

        foo = Foo()
        pytest.raises(TypeCheckError, foo.method, 1).match(
            rf'argument "another" \(int\) is not an instance of the self type '
            rf"\({__name__}\.{self.__class__.__name__}\."
            rf"test_classmethod_arg_invalid\.<locals>\.Foo\)"
        )

    def test_self_type_valid(self):
        class Foo:
            @typechecked
            def method(cls, subclass: type[Self]) -> None:
                pass

        class Bar(Foo):
            pass

        Foo().method(Bar)

    def test_self_type_invalid(self):
        class Foo:
            @typechecked
            def method(cls, subclass: type[Self]) -> None:
                pass

        pytest.raises(TypeCheckError, Foo().method, int).match(
            rf'argument "subclass" \(class int\) is not a subclass of the self type '
            rf"\({__name__}\.{self.__class__.__name__}\."
            rf"test_self_type_invalid\.<locals>\.Foo\)"
        )


class TestMock:
    def test_mock_argument(self):
        @typechecked
        def foo(x: int) -> None:
            pass

        foo(Mock())

    def test_return_mock(self):
        @typechecked
        def foo() -> int:
            return Mock()

        foo()


def test_decorator_before_classmethod():
    class Foo:
        @typechecked
        @classmethod
        def method(cls, x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_classmethod():
    @typechecked
    class Foo:
        @classmethod
        def method(cls, x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_decorator_before_staticmethod():
    class Foo:
        @typechecked
        @staticmethod
        def method(x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_staticmethod():
    @typechecked
    class Foo:
        @staticmethod
        def method(x: int) -> None:
            pass

    pytest.raises(TypeCheckError, Foo().method, "bar").match(
        r'argument "x" \(str\) is not an instance of int'
    )


def test_retain_dunder_attributes():
    @typechecked
    def foo(x: int, y: str = "foo") -> None:
        """This is a docstring."""

    assert foo.__module__ == __name__
    assert foo.__name__ == "foo"
    assert foo.__qualname__ == "test_retain_dunder_attributes.<locals>.foo"
    assert foo.__doc__ == "This is a docstring."
    assert foo.__defaults__ == ("foo",)


def test_debug_instrumentation(monkeypatch, capsys):
    monkeypatch.setattr("typeguard.config.debug_instrumentation", True)

    @typechecked
    def foo(a: str) -> int:
        return 6

    err = capsys.readouterr().err
    assert err == dedent(
        """\
        Source code of test_debug_instrumentation.<locals>.foo() after instrumentation:
        ----------------------------------------------
        def foo(a: str) -> int:
            from typeguard import TypeCheckMemo
            from typeguard._functions import check_argument_types_internal, \
check_return_type_internal
            memo = TypeCheckMemo(globals(), locals())
            check_argument_types_internal('test_debug_instrumentation.<locals>.foo', \
{'a': (a, str)}, memo)
            return check_return_type_internal('test_debug_instrumentation.<locals>.foo', \
6, int, memo)
        ----------------------------------------------
        """
    )


def test_keyword_argument_default():
    # Regression test for #305
    @typechecked
    def foo(*args, x: "int | None" = None):
        pass

    foo()


def test_return_type_annotation_refers_to_nonlocal():
    class Internal:
        pass

    @typechecked
    def foo() -> Internal:
        return Internal()

    assert isinstance(foo(), Internal)


def test_existing_method_decorator():
    @typechecked
    class Foo:
        @contextmanager
        def method(self, x: int) -> None:
            yield x + 1

    with Foo().method(6) as value:
        assert value == 7


@pytest.mark.parametrize(
    "flags, expected_return_code",
    [
        pytest.param([], 1, id="debug"),
        pytest.param(["-O"], 0, id="O"),
        pytest.param(["-OO"], 0, id="OO"),
    ],
)
def test_typechecked_disabled_in_optimized_mode(
    tmp_path: Path, flags: List[str], expected_return_code: int
):
    code = dedent(
        """
        from typeguard import typechecked

        @typechecked
        def foo(x: int) -> None:
            pass

        foo("a")
        """
    )
    script_path = tmp_path / "code.py"
    script_path.write_text(code)
    process = subprocess.run(
        [sys.executable, *flags, str(script_path)], capture_output=True, check=False
    )
    assert process.returncode == expected_return_code
    if process.returncode == 1:
        assert process.stderr.strip().endswith(
            b'typeguard.TypeCheckError: argument "x" (str) is not an instance of int'
        )


def test_reference_imported_name_from_method() -> None:
    # Regression test for #362
    @typechecked
    class A:
        def foo(self) -> Dict[str, Any]:
            return {}

    A().foo()


def test_getter_setter():
    """Regression test for #355."""

    @typechecked
    class Foo:
        def __init__(self, x: int):
            self._x = x

        @property
        def x(self) -> int:
            return self._x

        @x.setter
        def x(self, value: int) -> None:
            self._x = value

    f = Foo(1)
    f.x = 2
    assert f.x == 2
    with pytest.raises(TypeCheckError):
        f.x = "foo"


def test_duplicate_method():
    class Foo:
        def x(self) -> str:
            return "first"

        @typechecked()
        def x(self, value: int) -> str:  # noqa: F811
            return "second"

    assert Foo().x(1) == "second"
    with pytest.raises(TypeCheckError):
        Foo().x("wrong")


def test_duplicate_function():
    @typechecked
    def foo() -> list[int]:
        return [x for x in range(5)]

    foo1 = foo

    @typechecked
    def foo() -> list[int]:
        return [x for x in range(5, 10)]

    assert foo1() == [0, 1, 2, 3, 4]
    assert foo() == [5, 6, 7, 8, 9]


class TestAssignmentExpression:
    def test_non_iterable_value(self):
        @typechecked
        def foo() -> int:
            x: int = 0
            if (x := 5) > 0:
                pass

            return x

        assert foo() == 5

    def test_value_is_not_consumed(self):
        @typechecked
        def foo() -> str:
            x: str = "init"
            if x := "abc":
                pass

            return x

        assert foo() == "abc"

    def test_annotated_argument(self):
        @typechecked
        def foo(x: str) -> str:
            if x := "abc":
                pass

            return x

        assert foo("init") == "abc"

    def test_iterator_value_is_not_consumed(self):
        @typechecked
        def foo() -> Iterator[int]:
            x: Iterator[int] = iter([])
            if x := iter([1, 2, 3]):
                pass

            return x

        assert list(foo()) == [1, 2, 3]

    def test_bad_value_still_raises(self):
        @typechecked
        def foo() -> None:
            x: int = 0
            if (x := "not an int") is not None:  # noqa: F841
                pass

        with pytest.raises(
            TypeCheckError,
            match=r"value assigned to x \(str\) is not an instance of int",
        ):
            foo()


class TestInjectedNameCollisions:
    """Regression tests for https://github.com/agronholm/typeguard/issues/618.

    The instrumented functions live in throwaway modules because the name
    collisions only manifest for module level functions.
    """

    @staticmethod
    def import_module(tmp_path, monkeypatch, name: str, source: str):
        (tmp_path / f"{name}.py").write_text(
            "from typeguard import typechecked\n\n" + source
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        return __import__(name)

    def test_unread_parameter_named_memo(self, tmp_path, monkeypatch):
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_unread_memo",
            "@typechecked\ndef foo(memo: int) -> None:\n    pass\n",
        )
        module.foo(5)

    def test_except_alias_named_memo(self, tmp_path, monkeypatch):
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_except_memo",
            "@typechecked\n"
            "def foo(x: int) -> int:\n"
            "    try:\n"
            "        raise ValueError\n"
            "    except ValueError as memo:\n"
            "        pass\n"
            "    return x\n",
        )
        assert module.foo(1) == 1

    def test_match_capture_named_memo(self, tmp_path, monkeypatch):
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_match_memo",
            "@typechecked\n"
            "def foo(x: int) -> int:\n"
            "    match x:\n"
            "        case memo:\n"
            "            pass\n"
            '    return "not an int"\n',
        )
        with pytest.raises(
            TypeCheckError, match=r"the return value \(str\) is not an instance of int"
        ):
            module.foo(1)

    def test_global_named_memo(self, tmp_path, monkeypatch):
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_global_memo",
            "@typechecked\ndef foo(x: int) -> int:\n    global memo\n    return x\n",
        )
        assert module.foo(3) == 3

    def test_parameter_named_locals(self, tmp_path, monkeypatch):
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_param_locals",
            "@typechecked\ndef foo(x: int, locals=None) -> int:\n    return x\n",
        )
        assert module.foo(1) == 1

    def test_parameter_named_tuple(self, tmp_path, monkeypatch):
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_param_tuple",
            "@typechecked\ndef foo(*args: int, tuple=None) -> None:\n    pass\n",
        )
        module.foo(1, 2)

    def test_nested_function_name_not_shadowed(self, tmp_path, monkeypatch):
        # "memo" only exists via the wildcard import, so the instrumentation
        # cannot see it being bound anywhere in this module.
        (tmp_path / "star_provider.py").write_text(
            "class _StarMemo:\n"
            "    def __getitem__(self, item):\n"
            '        return "star-memo-result"\n\n\n'
            "memo = _StarMemo()\n"
            '__all__ = ["memo"]\n'
        )
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_nested_star",
            "from star_provider import *\n\n\n"
            "@typechecked\n"
            "def foo(x: int) -> object:\n"
            "    def inner() -> object:\n"
            "        return memo[0]\n"
            "    return inner()\n",
        )
        assert module.foo(1) == "star-memo-result"

    def test_string_annotation_name_not_shadowed(self, tmp_path, monkeypatch):
        (tmp_path / "star_provider2.py").write_text(
            'class memo:\n    pass\n\n\n__all__ = ["memo"]\n'
        )
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_string_anno",
            "from star_provider2 import *\n\n\n"
            '@typechecked\ndef foo(x: "memo") -> object:\n    return x\n',
        )
        assert isinstance(module.foo(module.memo()), module.memo)
        with pytest.raises(TypeCheckError):
            module.foo(5)

    def test_forward_reference_not_shadowed_by_injected_import(
        self, tmp_path, monkeypatch
    ):
        # The alias lives in another module where TypeCheckMemo means int;
        # the name must not be resolved against the injected import.
        (tmp_path / "alias_provider.py").write_text(
            "from typing import List\n\n"
            "TypeCheckMemo = int\n"
            'Alias = List["TypeCheckMemo"]\n'
        )
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "alias_consumer",
            "from alias_provider import Alias\n\n\n"
            "@typechecked\n"
            "def foo(x: Alias) -> None:\n"
            "    pass\n",
        )
        # The forward reference can no longer be resolved from this module,
        # but it must not be resolved against typeguard's own TypeCheckMemo
        # either (which would reject the perfectly valid [1, 2] argument).
        with pytest.warns(
            TypeHintWarning, match="Cannot resolve forward reference 'TypeCheckMemo'"
        ):
            module.foo([1, 2])

    def test_module_level_tuple_shadowing(self, tmp_path, monkeypatch):
        # A module level name shadowing a builtin called by the injected
        # code must not break the check (previously: TypeError from
        # `tuple[int, ...]` resolving to the module level `tuple = 123`).
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_module_tuple",
            "tuple = 123\n\n\n"
            "@typechecked\n"
            "def mod_fn(*args: int) -> None:\n"
            "    pass\n",
        )
        module.mod_fn(1, 2)
        with pytest.raises(TypeCheckError, match=r"is not an instance of int"):
            module.mod_fn("a")

    def test_module_level_tuple_shadowing_after_function(self, tmp_path, monkeypatch):
        # Same as above, but the shadowing assignment comes after the
        # function definition, so it is only seen via module level collection.
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_module_tuple_after",
            "@typechecked\n"
            "def mod_fn(*args: int) -> None:\n"
            "    pass\n\n\n"
            "tuple = 123\n",
        )
        module.mod_fn(1, 2)
        with pytest.raises(TypeCheckError, match=r"is not an instance of int"):
            module.mod_fn("a")

    def test_enclosing_scope_tuple_shadowing(self, tmp_path, monkeypatch):
        # A builtin shadowed in an enclosing function must not break the
        # injected code of a nested instrumented function (previously the
        # raw `Name("tuple")` became a free variable and tripped
        # `assert f.__closure__` in `_decorators.py`).
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_enclosing_tuple",
            "def outer():\n"
            "    tuple = 123\n\n"
            "    @typechecked\n"
            "    def inner(*args: int) -> None:\n"
            "        pass\n\n"
            "    return inner\n",
        )
        inner = module.outer()
        inner(1, 2)
        with pytest.raises(TypeCheckError, match=r"is not an instance of int"):
            inner("a")

    def test_module_level_globals_locals_shadowing(self, tmp_path, monkeypatch):
        # The injected memo construction calls `globals()` and `locals()`,
        # which must resolve to the real builtins even when the module
        # shadows those names.
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_module_globals_locals",
            "globals = 123\n"
            "locals = 456\n\n\n"
            "@typechecked\n"
            "def foo(x: int) -> int:\n"
            "    return x\n",
        )
        assert module.foo(1) == 1
        with pytest.raises(TypeCheckError, match=r"is not an instance of int"):
            module.foo("a")

    def test_module_level_dict_str_shadowing(self, tmp_path, monkeypatch):
        # The `**kwargs` annotation is built as `dict[str, ...]` by the
        # injected code, so module level `dict`/`str` bindings must not
        # leak into it.
        module = self.import_module(
            tmp_path,
            monkeypatch,
            "collision_module_dict_str",
            "dict = 123\n"
            "str = 456\n\n\n"
            "@typechecked\n"
            "def foo(**kwargs: int) -> None:\n"
            "    pass\n",
        )
        module.foo(a=1)
        with pytest.raises(TypeCheckError, match=r"is not an instance of int"):
            module.foo(a="x")

    @staticmethod
    def import_module_via_hook(tmp_path, monkeypatch, name: str, source: str):
        (tmp_path / f"{name}.py").write_text(source)
        monkeypatch.syspath_prepend(str(tmp_path))
        with install_import_hook([name]), warnings.catch_warnings():
            warnings.filterwarnings("error", module="typeguard")
            return import_module(name)

    def test_import_hook_module_except_alias_named_typecheckmemo(
        self, tmp_path, monkeypatch
    ):
        # Module level instrumentation injects the `TypeCheckMemo` import at
        # module level; a module level `except ... as TypeCheckMemo` clears
        # that name after the `except` block, so the import must be aliased
        # (previously: NameError inside instrumented functions).
        name = "collision_hook_except_memo"
        try:
            module = self.import_module_via_hook(
                tmp_path,
                monkeypatch,
                name,
                "try:\n"
                "    raise ValueError\n"
                "except ValueError as TypeCheckMemo:\n"
                "    pass\n\n\n"
                "def foo(x: int) -> int:\n"
                "    return x\n",
            )
            assert module.foo(1) == 1
        finally:
            sys.modules.pop(name, None)

    def test_import_hook_module_match_binding_named_typecheckmemo(
        self, tmp_path, monkeypatch
    ):
        # Same as above, but the module level binding comes from a `match`
        # capture, which would otherwise shadow the injected import with the
        # matched value (previously: TypeError calling it).
        name = "collision_hook_match_memo"
        try:
            module = self.import_module_via_hook(
                tmp_path,
                monkeypatch,
                name,
                "match 1:\n"
                "    case TypeCheckMemo:\n"
                "        pass\n\n\n"
                "def foo(x: int) -> int:\n"
                "    return x\n",
            )
            assert module.TypeCheckMemo == 1
            assert module.foo(1) == 1
        finally:
            sys.modules.pop(name, None)
