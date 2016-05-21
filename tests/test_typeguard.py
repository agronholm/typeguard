from functools import wraps, partial

from typing import Any, Callable, Dict, List, Set, Tuple, Union, TypeVar, Sequence

import pytest

from typeguard import typechecked, check_argument_types, qualified_name


class Parent:
    pass


class Child(Parent):
    def method(self, a: int):
        pass


@pytest.mark.parametrize('inputval, expected', [
    (qualified_name, 'typeguard.qualified_name'),
    (Child(), 'test_typeguard.Child'),
    (int, 'int')
], ids=['func', 'instance', 'builtintype'])
def test_qualified_name(inputval, expected):
    assert qualified_name(inputval) == expected


class TestCheckArgumentTypes:
    @pytest.mark.parametrize('args, kwargs', [
        ((), {1, 2}),
        ([1, 2], {})
    ])
    def test_wrong_arg_types(self, args, kwargs):
        def foo(a: int):
            pass

        exc = pytest.raises(TypeError, check_argument_types, foo, args, kwargs)
        assert str(exc.value) == 'args must be a tuple and kwargs must be a dict'

    def test_any_type(self):
        def foo(a: Any):
            assert check_argument_types()

        foo('aa')

    def test_callable(self):
        def foo(a: Callable[..., int]):
            assert check_argument_types()

        def some_callable() -> int:
            pass

        foo(some_callable)

    def test_callable_exact_arg_count(self):
        def foo(a: Callable[[int, str], int]):
            assert check_argument_types()

        def some_callable(x: int, y: str) -> int:
            pass

        foo(some_callable)

    def test_callable_bad_type(self):
        def foo(a: Callable[..., int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == 'argument a must be a callable'

    def test_callable_too_few_arguments(self):
        def foo(a: Callable[[int, str], int]):
            assert check_argument_types()

        def some_callable(x: int) -> int:
            pass

        exc = pytest.raises(TypeError, foo, some_callable)
        assert str(exc.value) == (
            'callable passed as argument a has too few arguments in its declaration; expected 2 '
            'but 1 argument(s) declared')

    def test_callable_too_many_arguments(self):
        def foo(a: Callable[[int, str], int]):
            assert check_argument_types()

        def some_callable(x: int, y: str, z: float) -> int:
            pass

        exc = pytest.raises(TypeError, foo, some_callable)
        assert str(exc.value) == (
            'callable passed as argument a has too many arguments in its declaration; expected '
            '2 but 3 argument(s) declared')

    def test_callable_mandatory_kwonlyargs(self):
        def foo(a: Callable[[int, str], int]):
            assert check_argument_types()

        def some_callable(x: int, y: str, *, z: float, bar: str) -> int:
            pass

        exc = pytest.raises(TypeError, foo, some_callable)
        assert str(exc.value) == (
            'callable passed as argument a has mandatory keyword-only arguments in its '
            'declaration: z, bar')

    def test_callable_class(self):
        """
        Test that passing a class as a callable does not count the "self" argument against the ones
        declared in the Callable specification.

        """
        def foo(a: Callable[[int, str], Any]):
            assert check_argument_types()

        class SomeClass:
            def __init__(self, x: int, y: str):
                pass

        foo(SomeClass)

    def test_callable_partial_class(self):
        """
        Test that passing a bound method as a callable does not count the "self" argument against
        the ones declared in the Callable specification.

        """
        def foo(a: Callable[[int], Any]):
            assert check_argument_types()

        class SomeClass:
            def __init__(self, x: int, y: str):
                pass

        foo(partial(SomeClass, y='foo'))

    def test_callable_bound_method(self):
        """
        Test that passing a bound method as a callable does not count the "self" argument against
        the ones declared in the Callable specification.

        """
        def foo(callback: Callable[[int], Any]):
            assert check_argument_types()

        foo(Child().method)

    def test_callable_partial_bound_method(self):
        """
        Test that passing a bound method as a callable does not count the "self" argument against
        the ones declared in the Callable specification.

        """
        def foo(callback: Callable[[], Any]):
            assert check_argument_types()

        foo(partial(Child().method, 1))

    def test_callable_defaults(self):
        """
        Test that a callable having "too many" arguments don't raise an error if the extra
        arguments have default values.

        """
        def foo(callback: Callable[[int, str], Any]):
            assert check_argument_types()

        def some_callable(x: int, y: str, z: float = 1.2) -> int:
            pass

        foo(some_callable)

    def test_callable_builtin(self):
        """
        Test that checking a Callable annotation against a builtin callable does not raise an
        error.

        """
        def foo(callback: Callable[[int], Any]):
            assert check_argument_types()

        foo([].append)

    def test_dict(self):
        def foo(a: Dict[str, int]):
            assert check_argument_types()

        foo({'x': 2})

    def test_dict_bad_type(self):
        def foo(a: Dict[str, int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument a must be a dict; got int instead')

    def test_dict_bad_key_type(self):
        def foo(a: Dict[str, int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, {1: 2})
        assert str(exc.value) == 'type of keys of argument a must be str; got int instead'

    def test_dict_bad_value_type(self):
        def foo(a: Dict[str, int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, {'x': 'a'})
        assert str(exc.value) == "type of argument a['x'] must be int; got str instead"

    def test_list(self):
        def foo(a: List[int]):
            assert check_argument_types()

        foo([1, 2])

    def test_list_bad_type(self):
        def foo(a: List[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument a must be a list; got int instead')

    def test_list_bad_element(self):
        def foo(a: List[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, [1, 2, 'bb'])
        assert str(exc.value) == (
            'type of argument a[2] must be int; got str instead')

    @pytest.mark.parametrize('value', [('a', 'b'), ['a', 'b'], 'abc'],
                             ids=['tuple', 'list', 'str'])
    def test_sequence(self, value):
        def foo(a: Sequence[str]):
            assert check_argument_types()

        foo(value)

    def test_sequence_bad_type(self):
        def foo(a: Sequence[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument a must be a sequence; got int instead')

    def test_sequence_bad_element(self):
        def foo(a: Sequence[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, [1, 2, 'bb'])
        assert str(exc.value) == (
            'type of argument a[2] must be int; got str instead')

    @pytest.mark.parametrize('value', [set(), {6}])
    def test_set(self, value):
        def foo(a: Set[int]):
            assert check_argument_types()

        foo(value)

    def test_set_bad_type(self):
        def foo(a: Set[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == 'type of argument a must be a set; got int instead'

    def test_set_bad_element(self):
        def foo(a: Set[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, {1, 2, 'bb'})
        assert str(exc.value) == (
            'type of elements of argument a must be int; got str instead')

    def test_tuple(self):
        def foo(a: Tuple[int, int]):
            assert check_argument_types()

        foo((1, 2))

    def test_tuple_bad_type(self):
        def foo(a: Tuple[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument a must be a tuple; got int instead')

    def test_tuple_wrong_number_of_elements(self):
        def foo(a: Tuple[int, str]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, (1, 'aa', 2))
        assert str(exc.value) == ('argument a has wrong number of elements (expected 2, got 3 '
                                  'instead)')

    def test_tuple_bad_element(self):
        def foo(a: Tuple[int, str]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, (1, 2))
        assert str(exc.value) == (
            'type of argument a[1] must be str; got int instead')

    @pytest.mark.parametrize('value', [6, 'aa'])
    def test_union(self, value):
        def foo(a: Union[str, int]):
            assert check_argument_types()

        foo(value)

    @pytest.mark.parametrize('value', [6.5, b'aa'])
    def test_union_fail(self, value):
        def foo(a: Union[str, int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, value)
        assert str(exc.value) == (
            'type of argument a must be one of (str, int); got {} instead'.
            format(value.__class__.__name__))

    @pytest.mark.parametrize('values', [
        (6, 7),
        ('aa', 'bb')
    ], ids=['int', 'str'])
    def test_typevar_constraints(self, values):
        T = TypeVar('T', int, str)

        def foo(a: T, b: T):
            assert check_argument_types()

        foo(*values)

    def test_typevar_constraints_fail(self):
        T = TypeVar('T', int, str)

        def foo(a: T, b: T):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 2.5, 'aa')
        assert str(exc.value) == 'type of argument a must be one of (int, str); got float instead'

    def test_typevar_bound(self):
        T = TypeVar('T', bound=Parent)

        def foo(a: T, b: T):
            assert check_argument_types()

        foo(Child(), Child())

    def test_typevar_bound_fail(self):
        T = TypeVar('T', bound=Child)

        def foo(a: T, b: T):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, Parent(), Parent())
        assert str(exc.value) == ('argument a must be an instance of test_typeguard.Child; got '
                                  'test_typeguard.Parent instead')

    def test_typevar_invariant_fail(self):
        T = TypeVar('T', int, str)

        def foo(a: T, b: T):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 2, 3.6)
        assert str(exc.value) == 'type of argument b must be exactly int; got float instead'

    def test_typevar_covariant(self):
        T = TypeVar('T', covariant=True)

        def foo(a: T, b: T):
            assert check_argument_types()

        foo(Parent(), Child())

    def test_typevar_covariant_fail(self):
        T = TypeVar('T', covariant=True)

        def foo(a: T, b: T):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, Child(), Parent())
        assert str(exc.value) == ('argument b must be an instance of test_typeguard.Child; got '
                                  'test_typeguard.Parent instead')

    def test_typevar_contravariant(self):
        T = TypeVar('T', contravariant=True)

        def foo(a: T, b: T):
            assert check_argument_types()

        foo(Child(), Parent())

    def test_typevar_contravariant_fail(self):
        T = TypeVar('T', contravariant=True)

        def foo(a: T, b: T):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, Parent(), Child())
        assert str(exc.value) == ('type of argument b must be test_typeguard.Parent or one of its '
                                  'superclasses; got test_typeguard.Child instead')

    def test_wrapped_function(self):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

        @decorator
        def foo(a: 'Child'):
            assert check_argument_types(foo)

        exc = pytest.raises(TypeError, foo, Parent())
        assert str(exc.value) == ('type of argument a must be test_typeguard.Child; '
                                  'got test_typeguard.Parent instead')

    @pytest.mark.parametrize('values', [
        ('x', 1.2, 'y'),
        (2, 'x', None)
    ], ids=['declared', 'default'])
    def test_default_argument_type(self, values):
        """
        Checks that the type of the default argument is also accepted even if it does not match the
        declared type of the argument.

        """
        def foo(a: str=1, b: float='x', c: str=None):
            assert check_argument_types()

        foo(*values)


class TestTypeChecked:
    def test_typechecked(self):
        @typechecked
        def foo(a: int, b: str) -> str:
            return 'abc'

        assert foo(4, 'abc') == 'abc'

    def test_typechecked_always(self):
        @typechecked(always=True)
        def foo(a: int, b: str) -> str:
            return 'abc'

        assert foo(4, 'abc') == 'abc'

    def test_typechecked_arguments_fail(self):
        @typechecked
        def foo(a: int, b: str) -> str:
            return 'abc'

        exc = pytest.raises(TypeError, foo, 4, 5)
        assert str(exc.value) == 'type of argument b must be str; got int instead'

    def test_typechecked_return_type_fail(self):
        @typechecked
        def foo(a: int, b: str) -> str:
            return 6

        exc = pytest.raises(TypeError, foo, 4, 'abc')
        func_name = qualified_name(foo)
        assert str(exc.value) == (
            'type of the return value of {}() must be str; got int instead'.format(func_name))

    def test_typechecked_return_typevar_fail(self):
        T = TypeVar('T', int, float)

        @typechecked
        def foo(a: T, b: T) -> T:
            return 'a'

        exc = pytest.raises(TypeError, foo, 4, 2)
        func_name = qualified_name(foo)
        assert str(exc.value) == (
            'type of the return value of {}() must be exactly int; got str instead'.
            format(func_name))

    def test_typechecked_no_annotations(self, recwarn):
        def foo(a, b):
            pass

        typechecked(foo)

        func_name = qualified_name(foo)
        assert len(recwarn) == 1
        assert str(recwarn[0].message) == (
            'no type annotations present -- not typechecking {}'.format(func_name))
