import collections.abc
import sys
from contextlib import nullcontext
from functools import partial
from io import BytesIO, StringIO
from pathlib import Path
from typing import (
    IO,
    AbstractSet,
    Any,
    AnyStr,
    BinaryIO,
    Callable,
    Collection,
    ContextManager,
    Dict,
    ForwardRef,
    FrozenSet,
    Iterator,
    List,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    TextIO,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import pytest

from typeguard import (
    CollectionCheckStrategy,
    ForwardRefPolicy,
    TypeCheckError,
    TypeCheckMemo,
    TypeHintWarning,
    check_type,
    check_type_internal,
    suppress_type_checks,
)
from typeguard._utils import qualified_name

from . import (
    Child,
    Employee,
    JSONType,
    Parent,
    RuntimeProtocol,
    StaticProtocol,
    TChild,
    TIntStr,
    TParent,
    TTypingConstrained,
    myint,
    mylist,
)

if sys.version_info >= (3, 11):
    from typing import LiteralString

    SubclassableAny = Any
else:
    from typing_extensions import Any as SubclassableAny
    from typing_extensions import LiteralString

if sys.version_info >= (3, 10):
    from typing import Concatenate, ParamSpec, TypeGuard
else:
    from typing_extensions import Concatenate, ParamSpec, TypeGuard

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

P = ParamSpec("P")


class TestAnyStr:
    @pytest.mark.parametrize(
        "value", [pytest.param("bar", id="str"), pytest.param(b"bar", id="bytes")]
    )
    def test_valid(self, value):
        check_type(value, AnyStr)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 4, AnyStr).match(
            r"does not match any of the constraints \(bytes, str\)"
        )


class TestBytesLike:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(b"test", id="bytes"),
            pytest.param(bytearray(b"test"), id="bytearray"),
            pytest.param(memoryview(b"test"), id="memoryview"),
        ],
    )
    def test_valid(self, value):
        check_type(value, bytes)

    def test_fail(self):
        pytest.raises(TypeCheckError, check_type, "test", bytes).match(
            r"str is not bytes-like"
        )


class TestFloat:
    @pytest.mark.parametrize(
        "value", [pytest.param(3, id="int"), pytest.param(3.87, id="float")]
    )
    def test_valid(self, value):
        check_type(value, float)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, "foo", float).match(
            r"str is neither float or int"
        )


class TestComplexNumber:
    @pytest.mark.parametrize(
        "value",
        [
            pytest.param(3, id="int"),
            pytest.param(3.87, id="float"),
            pytest.param(3.87 + 8j, id="complex"),
        ],
    )
    def test_valid(self, value):
        check_type(value, complex)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, "foo", complex).match(
            "str is neither complex, float or int"
        )


class TestCallable:
    def test_any_args(self):
        def some_callable(x: int, y: str) -> int:
            pass

        check_type(some_callable, Callable[..., int])

    def test_exact_arg_count(self):
        def some_callable(x: int, y: str) -> int:
            pass

        check_type(some_callable, Callable[[int, str], int])

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Callable[..., int]).match(
            "is not callable"
        )

    def test_too_few_arguments(self):
        def some_callable(x: int) -> int:
            pass

        pytest.raises(
            TypeCheckError, check_type, some_callable, Callable[[int, str], int]
        ).match(
            r"has too few arguments in its declaration; expected 2 but 1 argument\(s\) "
            r"declared"
        )

    def test_too_many_arguments(self):
        def some_callable(x: int, y: str, z: float) -> int:
            pass

        pytest.raises(
            TypeCheckError, check_type, some_callable, Callable[[int, str], int]
        ).match(
            r"has too many mandatory positional arguments in its declaration; expected "
            r"2 but 3 mandatory positional argument\(s\) declared"
        )

    def test_mandatory_kwonlyargs(self):
        def some_callable(x: int, y: str, *, z: float, bar: str) -> int:
            pass

        pytest.raises(
            TypeCheckError, check_type, some_callable, Callable[[int, str], int]
        ).match(r"has mandatory keyword-only arguments in its declaration: z, bar")

    def test_class(self):
        """
        Test that passing a class as a callable does not count the "self" argument
        against the ones declared in the Callable specification.

        """

        class SomeClass:
            def __init__(self, x: int, y: str):
                pass

        check_type(SomeClass, Callable[[int, str], Any])

    def test_plain(self):
        def callback(a):
            pass

        check_type(callback, Callable)

    def test_partial_class(self):
        """
        Test that passing a bound method as a callable does not count the "self"
        argument against the ones declared in the Callable specification.

        """

        class SomeClass:
            def __init__(self, x: int, y: str):
                pass

        check_type(partial(SomeClass, y="foo"), Callable[[int], Any])

    def test_bound_method(self):
        """
        Test that passing a bound method as a callable does not count the "self"
        argument against the ones declared in the Callable specification.

        """
        check_type(Child().method, Callable[[int], Any])

    def test_partial_bound_method(self):
        """
        Test that passing a bound method as a callable does not count the "self"
        argument against the ones declared in the Callable specification.

        """
        check_type(partial(Child().method, 1), Callable[[], Any])

    def test_defaults(self):
        """
        Test that a callable having "too many" arguments don't raise an error if the
        extra arguments have default values.

        """

        def some_callable(x: int, y: str, z: float = 1.2) -> int:
            pass

        check_type(some_callable, Callable[[int, str], Any])

    def test_builtin(self):
        """
        Test that checking a Callable annotation against a builtin callable does not
        raise an error.

        """
        check_type([].append, Callable[[int], Any])

    def test_concatenate(self):
        """Test that ``Concatenate`` in the arglist is ignored."""
        check_type([].append, Callable[Concatenate[object, P], Any])

    def test_positional_only_arg_with_default(self):
        def some_callable(x: int = 1, /) -> None:
            pass

        check_type(some_callable, Callable[[int], Any])


class TestLiteral:
    def test_literal_union(self):
        annotation = Union[str, Literal[1, 6, 8]]
        check_type(6, annotation)
        pytest.raises(TypeCheckError, check_type, 4, annotation).match(
            r"int did not match any element in the union:\n"
            r"  str: is not an instance of str\n"
            r"  Literal\[1, 6, 8\]: is not any of \(1, 6, 8\)$"
        )

    def test_literal_nested(self):
        annotation = Literal[1, Literal["x", "a", Literal["z"]], 6, 8]
        check_type("z", annotation)
        pytest.raises(TypeCheckError, check_type, 4, annotation).match(
            r"int is not any of \(1, 'x', 'a', 'z', 6, 8\)$"
        )

    def test_literal_int_as_bool(self):
        pytest.raises(TypeCheckError, check_type, 0, Literal[False])
        pytest.raises(TypeCheckError, check_type, 1, Literal[True])

    def test_literal_illegal_value(self):
        pytest.raises(TypeError, check_type, 4, Literal[1, 1.1]).match(
            r"Illegal literal value: 1.1$"
        )


class TestMapping:
    class DummyMapping(collections.abc.Mapping):
        _values = {"a": 1, "b": 10, "c": 100}

        def __getitem__(self, index: str):
            return self._values[index]

        def __iter__(self):
            return iter(self._values)

        def __len__(self) -> int:
            return len(self._values)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Mapping[str, int]).match(
            "is not a mapping"
        )

    def test_bad_key_type(self):
        pytest.raises(
            TypeCheckError, check_type, TestMapping.DummyMapping(), Mapping[int, int]
        ).match(
            f"key 'a' of {__name__}.TestMapping.DummyMapping is not an instance of int"
        )

    def test_bad_value_type(self):
        pytest.raises(
            TypeCheckError, check_type, TestMapping.DummyMapping(), Mapping[str, str]
        ).match(
            f"value of key 'a' of {__name__}.TestMapping.DummyMapping is not an "
            f"instance of str"
        )

    def test_bad_key_type_full_check(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            {"x": 1, 3: 2},
            Mapping[str, int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("key 3 of dict is not an instance of str")

    def test_bad_value_type_full_check(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            {"x": 1, "y": "a"},
            Mapping[str, int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("value of key 'y' of dict is not an instance of int")

    def test_any_value_type(self):
        check_type(TestMapping.DummyMapping(), Mapping[str, Any])


class TestMutableMapping:
    class DummyMutableMapping(collections.abc.MutableMapping):
        _values = {"a": 1, "b": 10, "c": 100}

        def __getitem__(self, index: str):
            return self._values[index]

        def __setitem__(self, key, value):
            self._values[key] = value

        def __delitem__(self, key):
            del self._values[key]

        def __iter__(self):
            return iter(self._values)

        def __len__(self) -> int:
            return len(self._values)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, MutableMapping[str, int]).match(
            "is not a mutable mapping"
        )

    def test_bad_key_type(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            TestMutableMapping.DummyMutableMapping(),
            MutableMapping[int, int],
        ).match(
            f"key 'a' of {__name__}.TestMutableMapping.DummyMutableMapping is not an "
            f"instance of int"
        )

    def test_bad_value_type(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            TestMutableMapping.DummyMutableMapping(),
            MutableMapping[str, str],
        ).match(
            f"value of key 'a' of {__name__}.TestMutableMapping.DummyMutableMapping "
            f"is not an instance of str"
        )


class TestDict:
    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Dict[str, int]).match(
            "int is not a dict"
        )

    def test_bad_key_type(self):
        pytest.raises(TypeCheckError, check_type, {1: 2}, Dict[str, int]).match(
            "key 1 of dict is not an instance of str"
        )

    def test_bad_value_type(self):
        pytest.raises(TypeCheckError, check_type, {"x": "a"}, Dict[str, int]).match(
            "value of key 'x' of dict is not an instance of int"
        )

    def test_bad_key_type_full_check(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            {"x": 1, 3: 2},
            Dict[str, int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("key 3 of dict is not an instance of str")

    def test_bad_value_type_full_check(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            {"x": 1, "y": "a"},
            Dict[str, int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("value of key 'y' of dict is not an instance of int")


class TestTypedDict:
    @pytest.mark.parametrize(
        "value, total, error_re",
        [
            pytest.param({"x": 6, "y": "foo"}, True, None, id="correct"),
            pytest.param(
                {"y": "foo"},
                True,
                r'dict is missing required key\(s\): "x"',
                id="missing_x",
            ),
            pytest.param(
                {"x": 6, "y": 3}, True, "dict is not an instance of str", id="wrong_y"
            ),
            pytest.param(
                {"x": 6},
                True,
                r'is missing required key\(s\): "y"',
                id="missing_y_error",
            ),
            pytest.param({"x": 6}, False, None, id="missing_y_ok"),
            pytest.param(
                {"x": "abc"}, False, "dict is not an instance of int", id="wrong_x"
            ),
            pytest.param(
                {"x": 6, "foo": "abc"},
                False,
                r'dict has unexpected extra key\(s\): "foo"',
                id="unknown_key",
            ),
            pytest.param(
                None,
                True,
                "is not a dict",
                id="not_dict",
            ),
        ],
    )
    def test_typed_dict(
        self, value, total: bool, error_re: Optional[str], typing_provider
    ):
        class DummyDict(typing_provider.TypedDict, total=total):
            x: int
            y: str

        if error_re:
            pytest.raises(TypeCheckError, check_type, value, DummyDict).match(error_re)
        else:
            check_type(value, DummyDict)

    def test_inconsistent_keys_invalid(self, typing_provider):
        class DummyDict(typing_provider.TypedDict):
            x: int

        pytest.raises(
            TypeCheckError, check_type, {"x": 1, "y": 2, b"z": 3}, DummyDict
        ).match(r'dict has unexpected extra key\(s\): "y", "b\'z\'"')


class TestList:
    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, List[int]).match(
            "int is not a list"
        )

    def test_first_check_success(self):
        check_type(["aa", "bb", 1], List[str])

    def test_first_check_empty(self):
        check_type([], List[str])

    def test_first_check_fail(self):
        pytest.raises(TypeCheckError, check_type, ["bb"], List[int]).match(
            "list is not an instance of int"
        )

    def test_full_check_fail(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            [1, 2, "bb"],
            List[int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("list is not an instance of int")


class TestSequence:
    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Sequence[int]).match(
            "int is not a sequence"
        )

    @pytest.mark.parametrize(
        "value",
        [pytest.param([1, "bb"], id="list"), pytest.param((1, "bb"), id="tuple")],
    )
    def test_first_check_success(self, value):
        check_type(value, Sequence[int])

    def test_first_check_empty(self):
        check_type([], Sequence[int])

    def test_first_check_fail(self):
        pytest.raises(TypeCheckError, check_type, ["bb"], Sequence[int]).match(
            "list is not an instance of int"
        )

    def test_full_check_fail(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            [1, 2, "bb"],
            Sequence[int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("list is not an instance of int")


class TestAbstractSet:
    def test_custom_type(self):
        class DummySet(AbstractSet[int]):
            def __contains__(self, x: object) -> bool:
                return x == 1

            def __len__(self) -> int:
                return 1

            def __iter__(self) -> Iterator[int]:
                yield 1

        check_type(DummySet(), AbstractSet[int])

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, AbstractSet[int]).match(
            "int is not a set"
        )

    def test_first_check_fail(self, sample_set):
        # Create a set which, when iterated, returns "bb" as the first item
        pytest.raises(TypeCheckError, check_type, sample_set, AbstractSet[int]).match(
            "set is not an instance of int"
        )

    def test_full_check_fail(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            {1, 2, "bb"},
            AbstractSet[int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("set is not an instance of int")


class TestSet:
    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Set[int]).match("int is not a set")

    def test_valid(self):
        check_type({1, 2}, Set[int])

    def test_first_check_empty(self):
        check_type(set(), Set[int])

    def test_first_check_fail(self, sample_set: set):
        pytest.raises(TypeCheckError, check_type, sample_set, Set[int]).match(
            "set is not an instance of int"
        )

    def test_full_check_fail(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            {1, 2, "bb"},
            Set[int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("set is not an instance of int")


class TestFrozenSet:
    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, FrozenSet[int]).match(
            "int is not a frozenset"
        )

    def test_valid(self):
        check_type(frozenset({1, 2}), FrozenSet[int])

    def test_first_check_empty(self):
        check_type(frozenset(), FrozenSet[int])

    def test_first_check_fail(self, sample_set: set):
        pytest.raises(
            TypeCheckError, check_type, frozenset(sample_set), FrozenSet[int]
        ).match("set is not an instance of int")

    def test_full_check_fail(self):
        pytest.raises(
            TypeCheckError,
            check_type,
            frozenset({1, 2, "bb"}),
            FrozenSet[int],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("set is not an instance of int")

    def test_set_against_frozenset(self, sample_set: set):
        pytest.raises(TypeCheckError, check_type, sample_set, FrozenSet[int]).match(
            "set is not a frozenset"
        )


@pytest.mark.parametrize(
    "annotated_type",
    [
        pytest.param(Tuple, id="typing"),
        pytest.param(
            tuple,
            id="builtin",
            marks=[
                pytest.mark.skipif(
                    sys.version_info < (3, 9),
                    reason="builtins.tuple is not parametrizable before Python 3.9",
                )
            ],
        ),
    ],
)
class TestTuple:
    def test_bad_type(self, annotated_type: Any):
        pytest.raises(TypeCheckError, check_type, 5, annotated_type[int]).match(
            "int is not a tuple"
        )

    def test_first_check_empty(self, annotated_type: Any):
        check_type((), annotated_type[int, ...])

    def test_unparametrized_tuple(self, annotated_type: Any):
        check_type((5, "foo"), annotated_type)

    def test_unparametrized_tuple_fail(self, annotated_type: Any):
        pytest.raises(TypeCheckError, check_type, 5, annotated_type).match(
            "int is not a tuple"
        )

    def test_too_many_elements(self, annotated_type: Any):
        pytest.raises(
            TypeCheckError, check_type, (1, "aa", 2), annotated_type[int, str]
        ).match(r"tuple has wrong number of elements \(expected 2, got 3 instead\)")

    def test_too_few_elements(self, annotated_type: Any):
        pytest.raises(TypeCheckError, check_type, (1,), annotated_type[int, str]).match(
            r"tuple has wrong number of elements \(expected 2, got 1 instead\)"
        )

    def test_bad_element(self, annotated_type: Any):
        pytest.raises(
            TypeCheckError, check_type, (1, 2), annotated_type[int, str]
        ).match("tuple is not an instance of str")

    def test_ellipsis_bad_element(self, annotated_type: Any):
        pytest.raises(
            TypeCheckError, check_type, ("blah",), annotated_type[int, ...]
        ).match("tuple is not an instance of int")

    def test_ellipsis_bad_element_full_check(self, annotated_type: Any):
        pytest.raises(
            TypeCheckError,
            check_type,
            (1, 2, "blah"),
            annotated_type[int, ...],
            collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS,
        ).match("tuple is not an instance of int")

    def test_empty_tuple(self, annotated_type: Any):
        check_type((), annotated_type[()])

    def test_empty_tuple_fail(self, annotated_type: Any):
        pytest.raises(TypeCheckError, check_type, (1,), annotated_type[()]).match(
            "tuple is not an empty tuple"
        )


class TestNamedTuple:
    def test_valid(self):
        check_type(Employee("bob", 1), Employee)

    def test_type_mismatch(self):
        pytest.raises(TypeCheckError, check_type, ("bob", 1), Employee).match(
            r"tuple is not a named tuple of type tests.Employee"
        )

    def test_wrong_field_type(self):
        pytest.raises(TypeCheckError, check_type, Employee(2, 1), Employee).match(
            r"Employee is not an instance of str"
        )


class TestUnion:
    @pytest.mark.parametrize(
        "value", [pytest.param(6, id="int"), pytest.param("aa", id="str")]
    )
    def test_valid(self, value):
        check_type(value, Union[str, int])

    def test_typing_type_fail(self):
        pytest.raises(TypeCheckError, check_type, 1, Union[str, Collection]).match(
            "int did not match any element in the union:\n"
            "  str: is not an instance of str\n"
            "  Collection: is not an instance of collections.abc.Collection"
        )

    @pytest.mark.parametrize(
        "annotation",
        [
            pytest.param(Union[str, int], id="pep484"),
            pytest.param(
                ForwardRef("str | int"),
                id="pep604",
                marks=[
                    pytest.mark.skipif(
                        sys.version_info < (3, 10), reason="Requires Python 3.10+"
                    )
                ],
            ),
        ],
    )
    @pytest.mark.parametrize(
        "value", [pytest.param(6.5, id="float"), pytest.param(b"aa", id="bytes")]
    )
    def test_union_fail(self, annotation, value):
        qualname = qualified_name(value)
        pytest.raises(TypeCheckError, check_type, value, annotation).match(
            f"{qualname} did not match any element in the union:\n"
            f"  str: is not an instance of str\n"
            f"  int: is not an instance of int"
        )

    @pytest.mark.skipif(
        sys.implementation.name != "cpython",
        reason="Test relies on CPython's reference counting behavior",
    )
    def test_union_reference_leak(self):
        leaked = True

        class Leak:
            def __del__(self):
                nonlocal leaked
                leaked = False

        def inner1():
            leak = Leak()  # noqa: F841
            check_type(b"asdf", Union[str, bytes])

        inner1()
        assert not leaked

        leaked = True

        def inner2():
            leak = Leak()  # noqa: F841
            with pytest.raises(TypeCheckError, match="any element in the union:"):
                check_type(1, Union[str, bytes])

        inner2()
        assert not leaked


class TestTypevar:
    def test_bound(self):
        check_type(Child(), TParent)

    def test_bound_fail(self):
        with pytest.raises(TypeCheckError, match="is not an instance of tests.Child"):
            check_type(Parent(), TChild)

    @pytest.mark.parametrize(
        "value", [pytest.param([6, 7], id="int"), pytest.param({"aa", "bb"}, id="str")]
    )
    def test_collection_constraints(self, value):
        check_type(value, TTypingConstrained)

    def test_collection_constraints_fail(self):
        pytest.raises(TypeCheckError, check_type, {1, 2}, TTypingConstrained).match(
            r"set does not match any of the constraints \(List\[int\], "
            r"AbstractSet\[str\]\)"
        )

    def test_constraints_fail(self):
        pytest.raises(TypeCheckError, check_type, 2.5, TIntStr).match(
            r"float does not match any of the constraints \(int, str\)"
        )


class TestNewType:
    def test_simple_valid(self):
        check_type(1, myint)

    def test_simple_bad_value(self):
        pytest.raises(TypeCheckError, check_type, "a", myint).match(
            r"str is not an instance of int"
        )

    def test_generic_valid(self):
        check_type([1], mylist)

    def test_generic_bad_value(self):
        pytest.raises(TypeCheckError, check_type, ["a"], mylist).match(
            r"item 0 of list is not an instance of int"
        )


class TestType:
    @pytest.mark.parametrize("annotation", [pytest.param(Type), pytest.param(type)])
    def test_unparametrized(self, annotation: Any):
        check_type(TestNewType, annotation)

    @pytest.mark.parametrize("annotation", [pytest.param(Type), pytest.param(type)])
    def test_unparametrized_fail(self, annotation: Any):
        pytest.raises(TypeCheckError, check_type, 1, annotation).match(
            "int is not a class"
        )

    @pytest.mark.parametrize(
        "value", [pytest.param(Parent, id="exact"), pytest.param(Child, id="subclass")]
    )
    def test_parametrized(self, value):
        check_type(value, Type[Parent])

    def test_parametrized_fail(self):
        pytest.raises(TypeCheckError, check_type, int, Type[str]).match(
            "class int is not a subclass of str"
        )

    @pytest.mark.parametrize(
        "value", [pytest.param(str, id="str"), pytest.param(int, id="int")]
    )
    def test_union(self, value):
        check_type(value, Type[Union[str, int, list]])

    def test_union_any(self):
        check_type(list, Type[Union[str, int, Any]])

    def test_any(self):
        check_type(list, Type[Any])

    def test_union_fail(self):
        pytest.raises(
            TypeCheckError, check_type, dict, Type[Union[str, int, list]]
        ).match(
            "class dict did not match any element in the union:\n"
            "  str: is not a subclass of str\n"
            "  int: is not a subclass of int\n"
            "  list: is not a subclass of list"
        )

    def test_union_typevar(self):
        T = TypeVar("T", bound=Parent)
        check_type(Child, Type[T])

    def test_generic_aliase(self):
        if sys.version_info >= (3, 9):
            check_type(dict[str, str], type)
        check_type(Dict, Type[Any])
        check_type(Dict[str, str], Type[Any])


class TestIO:
    @pytest.mark.parametrize(
        "annotation",
        [
            pytest.param(BinaryIO, id="direct"),
            pytest.param(IO[bytes], id="parametrized"),
        ],
    )
    def test_binary_valid(self, annotation):
        check_type(BytesIO(), annotation)

    @pytest.mark.parametrize(
        "annotation",
        [
            pytest.param(BinaryIO, id="direct"),
            pytest.param(IO[bytes], id="parametrized"),
        ],
    )
    def test_binary_fail(self, annotation):
        pytest.raises(TypeCheckError, check_type, StringIO(), annotation).match(
            "_io.StringIO is not a binary I/O object"
        )

    def test_binary_real_file(self, tmp_path: Path):
        with tmp_path.joinpath("testfile").open("wb") as f:
            check_type(f, BinaryIO)

    @pytest.mark.parametrize(
        "annotation",
        [pytest.param(TextIO, id="direct"), pytest.param(IO[str], id="parametrized")],
    )
    def test_text_valid(self, annotation):
        check_type(StringIO(), annotation)

    @pytest.mark.parametrize(
        "annotation",
        [pytest.param(TextIO, id="direct"), pytest.param(IO[str], id="parametrized")],
    )
    def test_text_fail(self, annotation):
        pytest.raises(TypeCheckError, check_type, BytesIO(), annotation).match(
            "_io.BytesIO is not a text based I/O object"
        )

    def test_text_real_file(self, tmp_path: Path):
        with tmp_path.joinpath("testfile").open("w") as f:
            check_type(f, TextIO)


class TestProtocol:
    def test_protocol(self):
        class Foo:
            member = 1

            def meth(self) -> None:
                pass

        check_type(Foo(), RuntimeProtocol)
        check_type(Foo, Type[RuntimeProtocol])

    def test_protocol_warns_on_static(self):
        class Foo:
            member = 1

            def meth(self) -> None:
                pass

        with pytest.warns(
            UserWarning, match=r"Typeguard cannot check the StaticProtocol protocol.*"
        ) as warning:
            check_type(Foo(), StaticProtocol)

        assert warning.list[0].filename == __file__

        with pytest.warns(
            UserWarning, match=r"Typeguard cannot check the StaticProtocol protocol.*"
        ) as warning:
            check_type(Foo, Type[StaticProtocol])

        assert warning.list[0].filename == __file__

    def test_fail_non_method_members(self):
        class Foo:
            val = 1

            def meth(self) -> None:
                pass

        clsname = f"{__name__}.TestProtocol.test_fail_non_method_members.<locals>.Foo"
        pytest.raises(TypeCheckError, check_type, Foo(), RuntimeProtocol).match(
            f"{clsname} is not compatible with the RuntimeProtocol protocol"
        )
        pytest.raises(TypeCheckError, check_type, Foo, Type[RuntimeProtocol]).match(
            f"class {clsname} is not compatible with the RuntimeProtocol protocol"
        )

    def test_fail(self):
        class Foo:
            def meth2(self) -> None:
                pass

        pattern = (
            f"{__name__}.TestProtocol.test_fail.<locals>.Foo is not compatible with "
            f"the RuntimeProtocol protocol"
        )
        pytest.raises(TypeCheckError, check_type, Foo(), RuntimeProtocol).match(pattern)
        pytest.raises(TypeCheckError, check_type, Foo, Type[RuntimeProtocol]).match(
            pattern
        )


class TestRecursiveType:
    def test_valid(self):
        check_type({"a": [1, 2, 3]}, JSONType)

    def test_fail(self):
        with pytest.raises(
            TypeCheckError,
            match=(
                "dict did not match any element in the union:\n"
                "  str: is not an instance of str\n"
                "  float: is neither float or int\n"
                "  bool: is not an instance of bool\n"
                "  NoneType: is not an instance of NoneType\n"
                "  List\\[JSONType\\]: is not a list\n"
                "  Dict\\[str, JSONType\\]: value of key 'a' did not match any element "
                "in the union:\n"
                "    str: is not an instance of str\n"
                "    float: is neither float or int\n"
                "    bool: is not an instance of bool\n"
                "    NoneType: is not an instance of NoneType\n"
                "    List\\[JSONType\\]: is not a list\n"
                "    Dict\\[str, JSONType\\]: is not a dict"
            ),
        ):
            check_type({"a": (1, 2, 3)}, JSONType)


class TestAnnotated:
    def test_valid(self):
        check_type("aa", Annotated[str, "blah"])

    def test_fail(self):
        pytest.raises(TypeCheckError, check_type, 1, Annotated[str, "blah"]).match(
            "int is not an instance of str"
        )


class TestLiteralString:
    def test_valid(self):
        check_type("aa", LiteralString)

    def test_fail(self):
        pytest.raises(TypeCheckError, check_type, 1, LiteralString).match(
            "int is not an instance of str"
        )


class TestTypeGuard:
    def test_valid(self):
        check_type(True, TypeGuard)

    def test_fail(self):
        pytest.raises(TypeCheckError, check_type, 1, TypeGuard).match(
            "int is not an instance of bool"
        )


@pytest.mark.parametrize(
    "policy, contextmanager",
    [
        pytest.param(ForwardRefPolicy.ERROR, pytest.raises(NameError), id="error"),
        pytest.param(ForwardRefPolicy.WARN, pytest.warns(TypeHintWarning), id="warn"),
        pytest.param(ForwardRefPolicy.IGNORE, nullcontext(), id="ignore"),
    ],
)
def test_forward_reference_policy(
    policy: ForwardRefPolicy, contextmanager: ContextManager
):
    with contextmanager:
        check_type(1, ForwardRef("Foo"), forward_ref_policy=policy)  # noqa: F821


def test_any():
    assert check_type("aa", Any) == "aa"


def test_suppressed_checking():
    with suppress_type_checks():
        assert check_type("aa", int) == "aa"


def test_suppressed_checking_exception():
    with pytest.raises(RuntimeError), suppress_type_checks():
        assert check_type("aa", int) == "aa"
        raise RuntimeError

    pytest.raises(TypeCheckError, check_type, "aa", int)


def test_any_subclass():
    class Foo(SubclassableAny):
        pass

    check_type(Foo(), int)


def test_none():
    check_type(None, None)


def test_return_checked_value():
    value = {"foo": 1}
    assert check_type(value, Dict[str, int]) is value


def test_imported_str_forward_ref():
    value = {"foo": 1}
    memo = TypeCheckMemo(globals(), locals())
    pattern = r"Skipping type check against 'Dict\[str, int\]'"
    with pytest.warns(TypeHintWarning, match=pattern):
        check_type_internal(value, "Dict[str, int]", memo)


def test_check_against_tuple_success():
    check_type(1, (float, Union[str, int]))


def test_check_against_tuple_failure():
    pytest.raises(TypeCheckError, check_type, "aa", (int, bytes))
