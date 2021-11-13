import sys
from functools import partial
from io import BytesIO, StringIO
from pathlib import Path
from typing import (
    IO, AbstractSet, Any, AnyStr, BinaryIO, Callable, Collection, Dict, Iterator, List, Optional,
    Sequence, Set, TextIO, Tuple, Type, TypeVar, Union)
from unittest.mock import Mock

import pytest

from typeguard import check_type
from typeguard.exceptions import TypeCheckError

from . import (
    Child, Employee, JSONType, Parent, RuntimeProtocol, StaticProtocol, TChild, TIntStr, TParent,
    TTypingConstrained, myint)

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

if sys.version_info >= (3, 8):
    from typing import Literal, TypedDict
else:
    from typing_extensions import Literal, TypedDict


class TestAnyStr:
    @pytest.mark.parametrize('value', [
        pytest.param('bar', id='str'),
        pytest.param(b'bar', id='bytes')
    ])
    def test_valid(self, value):
        check_type(value, AnyStr)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 4, AnyStr).\
            match(r'does not match any of the constraints \(bytes, str\)')


class TestBytesLike:
    @pytest.mark.parametrize('value', [
        pytest.param(b'test', id='bytes'),
        pytest.param(bytearray(b'test'), id='bytearray'),
        pytest.param(memoryview(b'test'), id='memoryview')
    ])
    def test_valid(self, value):
        check_type(value, bytes)

    def test_fail(self):
        pytest.raises(TypeCheckError, check_type, 'test', bytes).\
            match(r'value is not bytes-like')


class TestFloat:
    @pytest.mark.parametrize('value', [
        pytest.param(3, id='int'),
        pytest.param(3.87, id='float')
    ])
    def test_valid(self, value):
        check_type(value, float)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 'foo', float).\
            match(r'value is neither float or int')


class TestComplexNumber:
    @pytest.mark.parametrize('value', [
        pytest.param(3, id='int'),
        pytest.param(3.87, id='float'),
        pytest.param(3.87 + 8j, id='complex')
    ])
    def test_valid(self, value):
        check_type(value, complex)

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 'foo', complex).\
            match(r'value is neither complex, float or int')


class TestCallable:
    def test_exact_arg_count(self):
        def some_callable(x: int, y: str) -> int:
            pass

        check_type(some_callable, Callable[[int, str], int])

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Callable[..., int]).\
            match('is not callable')

    def test_too_few_arguments(self):
        def some_callable(x: int) -> int:
            pass

        pytest.raises(TypeCheckError, check_type, some_callable, Callable[[int, str], int]).\
            match(r'has too few arguments in its declaration; expected 2 but 1 argument\(s\) '
                  r'declared')

    def test_too_many_arguments(self):
        def some_callable(x: int, y: str, z: float) -> int:
            pass

        pytest.raises(TypeCheckError, check_type, some_callable, Callable[[int, str], int]).\
            match(r'has too many arguments in its declaration; expected 2 but 3 argument\(s\) '
                  r'declared')

    def test_mandatory_kwonlyargs(self):
        def some_callable(x: int, y: str, *, z: float, bar: str) -> int:
            pass

        pytest.raises(TypeCheckError, check_type, some_callable, Callable[[int, str], int]).\
            match(r'has mandatory keyword-only arguments in its declaration: z, bar')

    def test_class(self):
        """
        Test that passing a class as a callable does not count the "self" argument "a"gainst the
        ones declared in the Callable specification.

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
        Test that passing a bound method as a callable does not count the "self" argument "a"gainst
        the ones declared in the Callable specification.

        """
        class SomeClass:
            def __init__(self, x: int, y: str):
                pass

        check_type(partial(SomeClass, y='foo'), Callable[[int], Any])

    def test_bound_method(self):
        """
        Test that passing a bound method as a callable does not count the "self" argument "a"gainst
        the ones declared in the Callable specification.

        """
        check_type(Child().method, Callable[[int], Any])

    def test_partial_bound_method(self):
        """
        Test that passing a bound method as a callable does not count the "self" argument "a"gainst
        the ones declared in the Callable specification.

        """
        check_type(partial(Child().method, 1), Callable[[], Any])

    def test_defaults(self):
        """
        Test that a callable having "too many" arguments don't raise an error if the extra
        arguments have default values.

        """
        def some_callable(x: int, y: str, z: float = 1.2) -> int:
            pass

        check_type(some_callable, Callable[[int, str], Any])

    def test_builtin(self):
        """
        Test that checking a Callable annotation against a builtin callable does not raise an
        error.

        """
        check_type([].append, Callable[[int], Any])


class TestLiteral:
    def test_literal_union(self):
        annotation = Union[str, Literal[1, 6, 8]]
        check_type(6, annotation)
        pytest.raises(TypeCheckError, check_type, 4, annotation).\
            match(r"value did not match any element in the union:\n"
                  r"  str: is not an instance of str\n"
                  r"  Literal\[1, 6, 8\]: is not any of \(1, 6, 8\)$")

    def test_literal_nested(self):
        annotation = Literal[1, Literal['x', 'a', Literal['z']], 6, 8]
        check_type('z', annotation)
        pytest.raises(TypeCheckError, check_type, 4, annotation).\
            match(r"value is not any of \(1, 'x', 'a', 'z', 6, 8\)$")

    def test_literal_illegal_value(self):
        pytest.raises(TypeError, check_type, 4, Literal[1, 1.1]).\
            match(r"Illegal literal value: 1.1$")


class TestDict:
    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Dict[str, int]).\
            match('is not a dict')

    def test_bad_key_type(self):
        pytest.raises(TypeCheckError, check_type, {1: 2}, Dict[str, int]).\
            match('is not an instance of str')

    def test_bad_value_type(self):
        pytest.raises(TypeCheckError, check_type, {'x': 'a'}, Dict[str, int]).\
            match(r"value is not an instance of int")


class TestTypedDict:
    @pytest.mark.parametrize('value, total, error_re', [
        pytest.param({'x': 6, 'y': 'foo'}, True, None, id='correct'),
        pytest.param({'y': 'foo'}, True, r'value is missing required key\(s\): "x"',
                     id='missing_x'),
        pytest.param({'x': 6, 'y': 3}, True, 'value is not an instance of str', id='wrong_y'),
        pytest.param({'x': 6}, True, r'is missing required key\(s\): "y"', id='missing_y_error'),
        pytest.param({'x': 6}, False, None, id='missing_y_ok'),
        pytest.param({'x': 'abc'}, False, 'value is not an instance of int', id='wrong_x'),
        pytest.param({'x': 6, 'foo': 'abc'}, False, r'value has unexpected extra key\(s\): "foo"',
                     id='unknown_key')
    ])
    def test_typed_dict(self, value, total: bool, error_re: Optional[str]):
        class DummyDict(TypedDict, total=total):
            x: int
            y: str

        if error_re:
            pytest.raises(TypeCheckError, check_type, value, DummyDict).match(error_re)
        else:
            check_type(value, DummyDict)


class TestList:
    def test_valid(self):
        check_type(['aa', 'bb'], List[str])

    def test_list_bad_element(self):
        pytest.raises(TypeCheckError, check_type, [1, 2, 'bb'], List[int]).\
            match('value is not an instance of int')


class TestSequence:
    @pytest.mark.parametrize('value', [
        pytest.param([1, 8], id='list'),
        pytest.param((1, 8), id='tuple')
    ])
    def test_valid(self, value):
        check_type(value, Sequence[int])

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Sequence[int]).\
            match('value is not a sequence')

    def test_sequence_bad_element(self):
        pytest.raises(TypeCheckError, check_type, [1, 2, 'bb'], Sequence[int]).\
            match('value is not an instance of int')


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
        pytest.raises(TypeCheckError, check_type, 5, AbstractSet[int]).\
            match('value is not a set')

    def test_bad_element(self):
        pytest.raises(TypeCheckError, check_type, {1, 2, 'bb'}, AbstractSet[int]).\
            match('value is not an instance of int')


class TestSet:
    def test_valid(self):
        check_type({1, 2}, Set[int])

    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Set[int]).\
            match('value is not a set')

    def test_bad_element(self):
        pytest.raises(TypeCheckError, check_type, {1, 2, 'bb'}, Set[int]).\
            match('value is not an instance of int')


class TestTuple:
    def test_bad_type(self):
        pytest.raises(TypeCheckError, check_type, 5, Tuple[int]).\
            match('value is not a tuple')

    def test_too_many_elements(self):
        pytest.raises(TypeCheckError, check_type, (1, 'aa', 2), Tuple[int, str]).\
            match(r'value has wrong number of elements \(expected 2, got 3 instead\)')

    def test_too_few_elements(self):
        pytest.raises(TypeCheckError, check_type, (1,), Tuple[int, str]).\
            match(r'value has wrong number of elements \(expected 2, got 1 instead\)')

    def test_bad_element(self):
        pytest.raises(TypeCheckError, check_type, (1, 2), Tuple[int, str]).\
            match('value is not an instance of str')

    def test_ellipsis_bad_element(self):
        pytest.raises(TypeCheckError, check_type, (1, 2, 'blah'), Tuple[int, ...]).\
            match('value is not an instance of int')

    def test_empty_tuple(self):
        check_type((), Tuple[()])

    def test_empty_tuple_fail(self):
        pytest.raises(TypeCheckError, check_type, (1,), Tuple[()]).\
            match('value is not an empty tuple')


class TestNamedTuple:
    def test_valid(self):
        check_type(Employee('bob', 1), Employee)

    def test_type_mismatch(self):
        pytest.raises(TypeCheckError, check_type, ('bob', 1), Employee).\
            match(r'value is not a named tuple of type tests.Employee')

    def test_wrong_field_type(self):
        pytest.raises(TypeCheckError, check_type, Employee(2, 1), Employee).\
            match(r'value is not an instance of str')


class TestUnion:
    @pytest.mark.parametrize('value', [
        pytest.param(6, id='int'),
        pytest.param('aa', id='str')
    ])
    def test_valid(self, value):
        check_type(value, Union[str, int])

    def test_typing_type_fail(self):
        pytest.raises(TypeCheckError, check_type, 1, Union[str, Collection]).\
            match('value did not match any element in the union:\n'
                  '  str: is not an instance of str\n'
                  '  Collection: is not an instance of collections.abc.Collection')

    @pytest.mark.parametrize('value', [6.5, b'aa'])
    def test_union_fail(self, value):
        pytest.raises(TypeCheckError, check_type, value, Union[str, int]).\
            match("value did not match any element in the union:\n"
                  "  str: is not an instance of str\n"
                  "  int: is not an instance of int")


class TestTypevar:
    def test_bound(self):
        check_type(Child(), TParent)

    def test_bound_fail(self):
        with pytest.raises(
            TypeCheckError,
            match='is not an instance of tests.Child'
        ):
            check_type(Parent(), TChild)

    @pytest.mark.parametrize('value', [
        pytest.param([6, 7], id='int'),
        pytest.param({'aa', 'bb'}, id='str')
    ])
    def test_collection_constraints(self, value):
        check_type(value, TTypingConstrained)

    def test_collection_constraints_fail(self):
        pytest.raises(TypeCheckError, check_type, {1, 2}, TTypingConstrained).\
            match(r'value does not match any of the constraints \(List\[int\], '
                  r'AbstractSet\[str\]\)')

    def test_constraints_fail(self):
        pytest.raises(TypeCheckError, check_type, 2.5, TIntStr).\
            match(r'value does not match any of the constraints \(int, str\)')


class TestNewType:
    def test_valid(self):
        check_type(1, myint)

    def test_bad_value(self):
        pytest.raises(TypeCheckError, check_type, 'a', myint).\
            match(r'value is not an instance of int')


class TestType:
    @pytest.mark.parametrize('annotation', [
        pytest.param(Type),
        pytest.param(type)
    ])
    def test_unparametrized(self, annotation: Any):
        check_type(TestNewType, annotation)

    @pytest.mark.parametrize('annotation', [
        pytest.param(Type),
        pytest.param(type)
    ])
    def test_unparametrized_fail(self, annotation: Any):
        pytest.raises(TypeCheckError, check_type, 1, annotation).\
            match('value is not a class')

    @pytest.mark.parametrize('value', [
        pytest.param(Parent, id='exact'),
        pytest.param(Child, id='subclass')
    ])
    def test_parametrized(self, value):
        check_type(value, Type[Parent])

    def test_parametrized_fail(self):
        pytest.raises(TypeCheckError, check_type, int, Type[str]).\
            match('value is not a subclass of str')

    @pytest.mark.parametrize('value', [
        pytest.param(str, id='str'),
        pytest.param(int, id='int')
    ])
    def test_union(self, value):
        check_type(value, Type[Union[str, int, list]])

    def test_union_any(self):
        check_type(list, Type[Union[str, int, Any]])

    def test_union_fail(self):
        pytest.raises(TypeCheckError, check_type, dict, Type[Union[str, int, list]]).\
            match("value did not match any element in the union:\n"
                  "  str: is not a subclass of str\n"
                  "  int: is not a subclass of int\n"
                  "  list: is not a subclass of list")

    def test_union_typevar(self):
        T = TypeVar('T', bound=Parent)
        check_type(Child, Type[T])


class TestIO:
    @pytest.mark.parametrize('annotation', [
        pytest.param(BinaryIO, id='direct'),
        pytest.param(IO[bytes], id='parametrized')
    ])
    def test_binary_valid(self, annotation):
        check_type(BytesIO(), annotation)

    @pytest.mark.parametrize('annotation', [
        pytest.param(BinaryIO, id='direct'),
        pytest.param(IO[bytes], id='parametrized')
    ])
    def test_binary_fail(self, annotation):
        pytest.raises(TypeCheckError, check_type, StringIO(), annotation).\
            match('value is not a binary I/O object')

    def test_binary_real_file(self, tmp_path: Path):
        with tmp_path.joinpath('testfile').open('wb') as f:
            check_type(f, BinaryIO)

    @pytest.mark.parametrize('annotation', [
        pytest.param(TextIO, id='direct'),
        pytest.param(IO[str], id='parametrized')
    ])
    def test_text_valid(self, annotation):
        check_type(StringIO(), annotation)

    @pytest.mark.parametrize('annotation', [
        pytest.param(TextIO, id='direct'),
        pytest.param(IO[str], id='parametrized')
    ])
    def test_text_fail(self, annotation):
        pytest.raises(TypeCheckError, check_type, BytesIO(), annotation).\
            match('value is not a text based I/O object')

    def test_text_real_file(self, tmp_path: Path):
        with tmp_path.joinpath('testfile').open('w') as f:
            check_type(f, TextIO)


class TestProtocol:
    @pytest.mark.parametrize('protocol_cls', [RuntimeProtocol, StaticProtocol])
    def test_protocol(self, protocol_cls):
        class Foo:
            member = 1

            def meth(self) -> None:
                pass

        check_type(Foo(), protocol_cls)

    def test_non_method_members(self):
        class Foo:
            member = 1

            def meth(self) -> None:
                pass

        check_type(Foo(), RuntimeProtocol)

    def test_fail(self):
        class Foo:
            def meth2(self) -> None:
                pass

        pytest.raises(TypeCheckError, check_type, Foo(), RuntimeProtocol).\
            match('value is not compatible with the RuntimeProtocol protocol')


class TestMock:
    def test_plain_mock(self):
        check_type(Mock(), Parent)

    @pytest.mark.parametrize('value_class', [
        pytest.param(Parent, id='parent'),
        pytest.param(Child, id='child'),
    ])
    def test_mock_with_spec(self, value_class):
        check_type(Mock(Parent), value_class)

    @pytest.mark.xfail(reason='Typeguard cannot support this yet')
    def test_mock_with_spec_fail(self):
        pytest.raises(TypeCheckError, check_type, Mock(Parent), Child)


class TestRecursiveType:
    def test_valid(self):
        check_type({'a': [1, 2, 3]}, JSONType)

    def test_fail(self):
        with pytest.raises(
            TypeCheckError,
            match=('value did not match any element in the union:\n'
                   '  str: is not an instance of str\n'
                   '  float: is neither float or int\n'
                   '  bool: is not an instance of bool\n'
                   '  NoneType: is not an instance of NoneType\n'
                   '  List\\[JSONType\\]: is not a list\n'
                   '  Dict\\[str, JSONType\\]: did not match any element in the union:\n'
                   '    str: is not an instance of str\n'
                   '    float: is neither float or int\n'
                   '    bool: is not an instance of bool\n'
                   '    NoneType: is not an instance of NoneType\n'
                   '    List\\[JSONType\\]: is not a list\n'
                   '    Dict\\[str, JSONType\\]: value is not a dict')
        ):
            check_type({'a': (1, 2, 3)}, JSONType)


class TestAnnotated:
    def test_valid(self):
        check_type('aa', Annotated[str, 'blah'])

    def test_fail(self):
        pytest.raises(TypeCheckError, check_type, 1, Annotated[str, 'blah']).\
            match('value is not an instance of str')


def test_any():
    check_type('aa', Any)
