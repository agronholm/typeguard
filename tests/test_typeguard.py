import sys
from concurrent.futures import ThreadPoolExecutor
from functools import wraps, partial
from io import StringIO

import pytest

from typeguard import (
    typechecked, check_argument_types, qualified_name, TypeChecker, TypeWarning, function_name)

try:
    from backports.typing import (
        Any, Callable, Dict, List, Set, Tuple, Union, TypeVar, Sequence, NamedTuple, Iterable,
        Container, Type)
except ImportError:
    from typing import (
        Any, Callable, Dict, List, Set, Tuple, Union, TypeVar, Sequence, NamedTuple, Iterable,
        Container)

    try:
        from typing import Type
    except ImportError:
        Type = List  # don't worry, Type is not actually used if this happens!


class Parent:
    pass


class Child(Parent):
    def method(self, a: int):
        pass


@pytest.mark.parametrize('inputval, expected', [
    (qualified_name, 'function'),
    (Child(), 'test_typeguard.Child'),
    (int, 'int')
], ids=['func', 'instance', 'builtintype'])
def test_qualified_name(inputval, expected):
    assert qualified_name(inputval) == expected


def test_function_name():
    assert function_name(function_name) == 'typeguard.function_name'


class TestCheckArgumentTypes:
    def test_any_type(self):
        def foo(a: Any):
            assert check_argument_types()

        foo('aa')

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
        assert str(exc.value) == 'argument "a" must be a callable'

    def test_callable_too_few_arguments(self):
        def foo(a: Callable[[int, str], int]):
            assert check_argument_types()

        def some_callable(x: int) -> int:
            pass

        exc = pytest.raises(TypeError, foo, some_callable)
        assert str(exc.value) == (
            'callable passed as argument "a" has too few arguments in its declaration; expected 2 '
            'but 1 argument(s) declared')

    def test_callable_too_many_arguments(self):
        def foo(a: Callable[[int, str], int]):
            assert check_argument_types()

        def some_callable(x: int, y: str, z: float) -> int:
            pass

        exc = pytest.raises(TypeError, foo, some_callable)
        assert str(exc.value) == (
            'callable passed as argument "a" has too many arguments in its declaration; expected '
            '2 but 3 argument(s) declared')

    def test_callable_mandatory_kwonlyargs(self):
        def foo(a: Callable[[int, str], int]):
            assert check_argument_types()

        def some_callable(x: int, y: str, *, z: float, bar: str) -> int:
            pass

        exc = pytest.raises(TypeError, foo, some_callable)
        assert str(exc.value) == (
            'callable passed as argument "a" has mandatory keyword-only arguments in its '
            'declaration: z, bar')

    def test_callable_class(self):
        """
        Test that passing a class as a callable does not count the "self" argument "a"gainst the
        ones declared in the Callable specification.

        """
        def foo(a: Callable[[int, str], Any]):
            assert check_argument_types()

        class SomeClass:
            def __init__(self, x: int, y: str):
                pass

        foo(SomeClass)

    def test_callable_partial_class(self):
        """
        Test that passing a bound method as a callable does not count the "self" argument "a"gainst
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
        Test that passing a bound method as a callable does not count the "self" argument "a"gainst
        the ones declared in the Callable specification.

        """
        def foo(callback: Callable[[int], Any]):
            assert check_argument_types()

        foo(Child().method)

    def test_callable_partial_bound_method(self):
        """
        Test that passing a bound method as a callable does not count the "self" argument "a"gainst
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

    def test_dict_bad_type(self):
        def foo(a: Dict[str, int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument "a" must be a dict; got int instead')

    def test_dict_bad_key_type(self):
        def foo(a: Dict[str, int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, {1: 2})
        assert str(exc.value) == 'type of keys of argument "a" must be str; got int instead'

    def test_dict_bad_value_type(self):
        def foo(a: Dict[str, int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, {'x': 'a'})
        assert str(exc.value) == "type of argument \"a\"['x'] must be int; got str instead"

    def test_list_bad_type(self):
        def foo(a: List[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument "a" must be a list; got int instead')

    def test_list_bad_element(self):
        def foo(a: List[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, [1, 2, 'bb'])
        assert str(exc.value) == (
            'type of argument "a"[2] must be int; got str instead')

    def test_sequence_bad_type(self):
        def foo(a: Sequence[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument "a" must be a sequence; got int instead')

    def test_sequence_bad_element(self):
        def foo(a: Sequence[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, [1, 2, 'bb'])
        assert str(exc.value) == (
            'type of argument "a"[2] must be int; got str instead')

    def test_set_bad_type(self):
        def foo(a: Set[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == 'type of argument "a" must be a set; got int instead'

    def test_set_bad_element(self):
        def foo(a: Set[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, {1, 2, 'bb'})
        assert str(exc.value) == (
            'type of elements of argument "a" must be int; got str instead')

    def test_tuple_bad_type(self):
        def foo(a: Tuple[int]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 5)
        assert str(exc.value) == (
            'type of argument "a" must be a tuple; got int instead')

    def test_tuple_too_many_elements(self):
        def foo(a: Tuple[int, str]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, (1, 'aa', 2))
        assert str(exc.value) == ('argument "a" has wrong number of elements (expected 2, got 3 '
                                  'instead)')

    def test_tuple_too_few_elements(self):
        def foo(a: Tuple[int, str]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, (1,))
        assert str(exc.value) == ('argument "a" has wrong number of elements (expected 2, got 1 '
                                  'instead)')

    def test_tuple_bad_element(self):
        def foo(a: Tuple[int, str]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, (1, 2))
        assert str(exc.value) == (
            'type of argument "a"[1] must be str; got int instead')

    def test_tuple_ellipsis_bad_element(self):
        def foo(a: Tuple[int, ...]):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, (1, 2, 'blah'))
        assert str(exc.value) == (
            'type of argument "a"[2] must be int; got str instead')

    def test_namedtuple(self):
        Employee = NamedTuple('Employee', [('name', str), ('id', int)])

        def foo(bar: Employee):
            assert check_argument_types()

        foo(Employee('bob', 1))

    def test_namedtuple_type_mismatch(self):
        Employee = NamedTuple('Employee', [('name', str), ('id', int)])

        def foo(bar: Employee):
            assert check_argument_types()

        pytest.raises(TypeError, foo, ('bob', 1)).\
            match('type of argument "bar" must be a named tuple of type '
                  '(test_typeguard\.)?Employee; got tuple instead')

    def test_namedtuple_wrong_field_type(self):
        Employee = NamedTuple('Employee', [('name', str), ('id', int)])

        def foo(bar: Employee):
            assert check_argument_types()

        pytest.raises(TypeError, foo, Employee(2, 1)).\
            match('type of argument "bar".name must be str; got int instead')

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
            'type of argument "a" must be one of (str, int); got {} instead'.
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
        assert str(exc.value) == ('type of argument "a" must be one of (int, str); got float '
                                  'instead')

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
        assert str(exc.value) == ('type of argument "a" must be test_typeguard.Child or one of '
                                  'its subclasses; got test_typeguard.Parent instead')

    def test_typevar_invariant_fail(self):
        T = TypeVar('T', int, str)

        def foo(a: T, b: T):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 2, 3.6)
        assert str(exc.value) == 'type of argument "b" must be exactly int; got float instead'

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
        assert str(exc.value) == ('type of argument "b" must be test_typeguard.Child or one of '
                                  'its subclasses; got test_typeguard.Parent instead')

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
        assert str(exc.value) == ('type of argument "b" must be test_typeguard.Parent or one of '
                                  'its superclasses; got test_typeguard.Child instead')

    @pytest.mark.skipif(Type is List, reason='typing.Type could not be imported')
    def test_class_bad_subclass(self):
        def foo(a: Type[Child]):
            assert check_argument_types()

        pytest.raises(TypeError, foo, Parent).match(
            '"a" must be a subclass of test_typeguard.Child; got test_typeguard.Parent instead')

    def test_wrapped_function(self):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

        @decorator
        def foo(a: 'Child'):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, Parent())
        assert str(exc.value) == ('type of argument "a" must be test_typeguard.Child; '
                                  'got test_typeguard.Parent instead')

    @pytest.mark.parametrize('values', [
        ('x', 1.2, 'y'),
        (2, 'x', None)
    ], ids=['declared', 'default'])
    def test_default_argument_type(self, values):
        """
        Test that the type of the default argument is also accepted even if it does not match the
        declared type of the argument.

        """
        def foo(a: str=1, b: float='x', c: str=None):
            assert check_argument_types()

        foo(*values)

    def test_generator(self):
        """Test that argument type checking works in a generator function too."""
        def generate(a: int):
            assert check_argument_types()
            yield a
            yield a + 1

        gen = generate(1)
        next(gen)

    def test_varargs(self):
        def foo(*args: int):
            assert check_argument_types()

        foo(1, 2)

    def test_varargs_fail(self):
        def foo(*args: int):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, 1, 'a')
        exc.match('type of argument "args"\[1\] must be int; got str instead')

    def test_kwargs(self):
        def foo(**kwargs: int):
            assert check_argument_types()

        foo(a=1, b=2)

    def test_kwargs_fail(self):
        def foo(**kwargs: int):
            assert check_argument_types()

        exc = pytest.raises(TypeError, foo, a=1, b='a')
        exc.match('type of argument "kwargs"\[\'b\'\] must be int; got str instead')


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
        assert str(exc.value) == 'type of argument "b" must be str; got int instead'

    def test_typechecked_return_type_fail(self):
        @typechecked
        def foo(a: int, b: str) -> str:
            return 6

        exc = pytest.raises(TypeError, foo, 4, 'abc')
        assert str(exc.value) == 'type of the return value must be str; got int instead'

    def test_typechecked_return_typevar_fail(self):
        T = TypeVar('T', int, float)

        @typechecked
        def foo(a: T, b: T) -> T:
            return 'a'

        exc = pytest.raises(TypeError, foo, 4, 2)
        assert str(exc.value) == 'type of the return value must be exactly int; got str instead'

    def test_typechecked_no_annotations(self, recwarn):
        def foo(a, b):
            pass

        typechecked(foo)

        func_name = function_name(foo)
        assert len(recwarn) == 1
        assert str(recwarn[0].message) == (
            'no type annotations present -- not typechecking {}'.format(func_name))

    def test_return_type_none(self):
        """Check that a declared return type of None is respected."""
        @typechecked
        def foo() -> None:
            return 'a'

        exc = pytest.raises(TypeError, foo)
        assert str(exc.value) == 'type of the return value must be NoneType; got str instead'

    @pytest.mark.parametrize('typehint', [
        Callable[..., int],
        Callable
    ], ids=['parametrized', 'unparametrized'])
    def test_callable(self, typehint):
        @typechecked
        def foo(a: typehint):
            pass

        def some_callable() -> int:
            pass

        foo(some_callable)

    @pytest.mark.parametrize('typehint', [
        List[int],
        List,
        list,
    ], ids=['parametrized', 'unparametrized', 'plain'])
    def test_list(self, typehint):
        @typechecked
        def foo(a: typehint):
            pass

        foo([1, 2])

    @pytest.mark.parametrize('typehint', [
        Dict[str, int],
        Dict,
        dict
    ], ids=['parametrized', 'unparametrized', 'plain'])
    def test_dict(self, typehint):
        @typechecked
        def foo(a: typehint):
            pass

        foo({'x': 2})

    @pytest.mark.parametrize('typehint', [
        Sequence[str],
        Sequence
    ], ids=['parametrized', 'unparametrized'])
    @pytest.mark.parametrize('value', [('a', 'b'), ['a', 'b'], 'abc'],
                             ids=['tuple', 'list', 'str'])
    def test_sequence(self, typehint, value):
        @typechecked
        def foo(a: typehint):
            pass

        foo(value)

    @pytest.mark.parametrize('typehint', [
        Iterable[str],
        Iterable
    ], ids=['parametrized', 'unparametrized'])
    @pytest.mark.parametrize('value', [('a', 'b'), ['a', 'b'], 'abc'],
                             ids=['tuple', 'list', 'str'])
    def test_iterable(self, typehint, value):
        @typechecked
        def foo(a: typehint):
            pass

        foo(value)

    @pytest.mark.parametrize('typehint', [
        Container[str],
        Container
    ], ids=['parametrized', 'unparametrized'])
    @pytest.mark.parametrize('value', [('a', 'b'), ['a', 'b'], 'abc'],
                             ids=['tuple', 'list', 'str'])
    def test_container(self, typehint, value):
        @typechecked
        def foo(a: typehint):
            pass

        foo(value)

    @pytest.mark.parametrize('typehint', [
        Set[int],
        Set,
        set
    ], ids=['parametrized', 'unparametrized', 'plain'])
    @pytest.mark.parametrize('value', [set(), {6}])
    def test_set(self, typehint, value):
        @typechecked
        def foo(a: typehint):
            pass

        foo(value)

    @pytest.mark.parametrize('typehint', [
        Tuple[int, int],
        Tuple[int, ...],
        Tuple,
        tuple
    ], ids=['parametrized', 'ellipsis', 'unparametrized', 'plain'])
    def test_tuple(self, typehint):
        @typechecked
        def foo(a: typehint):
            pass

        foo((1, 2))

    @pytest.mark.skipif(Type is List, reason='typing.Type could not be imported')
    @pytest.mark.parametrize('typehint', [
        Type[Parent],
        Type[TypeVar('UnboundType')],
        Type[TypeVar('BoundType', bound=Parent)],
        Type,
        type
    ], ids=['parametrized', 'unbound-typevar', 'bound-typevar', 'unparametrized', 'plain'])
    def test_class(self, typehint):
        @typechecked
        def foo(a: typehint):
            pass

        foo(Child)

    @pytest.mark.skipif(Type is List, reason='typing.Type could not be imported')
    def test_class_not_a_class(self):
        @typechecked
        def foo(a: Type[dict]):
            pass

        exc = pytest.raises(TypeError, foo, 1)
        exc.match('type of argument "a" must be a type; got int instead')


class TestTypeChecker:
    @pytest.fixture
    def executor(self):
        executor = ThreadPoolExecutor(1)
        yield executor
        executor.shutdown()

    @pytest.fixture
    def checker(self):
        return TypeChecker(__name__)

    def test_check_call_args(self, checker: TypeChecker):
        def foo(a: int):
            pass

        with checker, pytest.warns(TypeWarning) as record:
            assert checker.active
            foo(1)
            foo('x')

        assert not checker.active
        foo('x')

        assert len(record) == 1
        warning = record[0].message
        assert warning.error == 'type of argument "a" must be int; got str instead'
        assert warning.func is foo
        assert isinstance(warning.stack, list)
        buffer = StringIO()
        warning.print_stack(buffer)
        assert len(buffer.getvalue()) > 100

    def test_check_return_value(self, checker: TypeChecker):
        def foo() -> int:
            return 'x'

        with checker, pytest.warns(TypeWarning) as record:
            foo()

        assert len(record) == 1
        assert record[0].message.error == 'type of the return value must be int; got str instead'

    def test_threaded_check_call_args(self, checker: TypeChecker, executor):
        def foo(a: int):
            pass

        with checker, pytest.warns(TypeWarning) as record:
            executor.submit(foo, 1).result()
            executor.submit(foo, 'x').result()

        executor.submit(foo, 'x').result()

        assert len(record) == 1
        warning = record[0].message
        assert warning.error == 'type of argument "a" must be int; got str instead'
        assert warning.func is foo

    def test_double_start(self, checker: TypeChecker):
        """Test that the same type checker can't be started twice while running."""
        with checker:
            pytest.raises(RuntimeError, checker.start).match('type checker already running')

    def test_nested(self):
        """Test that nesting of type checker context managers works as expected."""
        def foo(a: int):
            pass

        with TypeChecker(__name__), pytest.warns(TypeWarning) as record:
            foo('x')
            with TypeChecker(__name__):
                foo('x')

        assert len(record) == 3

    def test_existing_profiler(self, checker: TypeChecker):
        """
        Test that an existing profiler function is chained with the type checker and restored after
        the block is exited.

        """
        def foo(a: int):
            pass

        def profiler(frame, event, arg):
            nonlocal profiler_run_count
            if event in ('call', 'return'):
                profiler_run_count += 1

            if old_profiler:
                old_profiler(frame, event, arg)

        profiler_run_count = 0
        old_profiler = sys.getprofile()
        sys.setprofile(profiler)
        try:
            with checker, pytest.warns(TypeWarning) as record:
                foo(1)
                foo('x')

            assert sys.getprofile() is profiler
        finally:
            sys.setprofile(old_profiler)

        assert profiler_run_count
        assert len(record) == 1
