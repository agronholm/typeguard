import asyncio
import sys
import warnings
from importlib import import_module
from importlib.util import cache_from_source
from pathlib import Path

import pytest
from pytest import FixtureRequest

from typeguard import TypeCheckError
from typeguard.importhook import install_import_hook

pytestmark = pytest.mark.filterwarnings("error:no type annotations present")
this_dir = Path(__file__).parent
dummy_module_path = this_dir / "dummymodule.py"
cached_module_path = Path(
    cache_from_source(str(dummy_module_path), optimization="typeguard")
)


@pytest.fixture(scope="module", params=["importhook", "typechecked"])
def method(request: FixtureRequest) -> str:
    return request.param


@pytest.fixture(scope="module")
def dummymodule(method: str):
    sys.path.insert(0, str(this_dir))
    try:
        if method == "typechecked":
            return import_module("dummymodule")

        if cached_module_path.exists():
            cached_module_path.unlink()

        with install_import_hook(["dummymodule"]):
            with warnings.catch_warnings():
                warnings.filterwarnings("error", module="typeguard")
                module = import_module("dummymodule")
                return module
    finally:
        sys.path.remove(str(this_dir))


def test_type_checked_func(dummymodule):
    assert dummymodule.type_checked_func(2, 3) == 6


def test_type_checked_func_error(dummymodule):
    pytest.raises(TypeCheckError, dummymodule.type_checked_func, 2, "3").match(
        'argument "y" is not an instance of int'
    )


def test_non_type_checked_func(dummymodule):
    assert dummymodule.non_type_checked_func("bah", 9) == "foo"


def test_non_type_checked_decorated_func(dummymodule):
    assert dummymodule.non_type_checked_func("bah", 9) == "foo"


def test_typeguard_ignored_func(dummymodule):
    assert dummymodule.non_type_checked_func("bah", 9) == "foo"


def test_type_checked_method(dummymodule):
    instance = dummymodule.DummyClass()
    pytest.raises(TypeCheckError, instance.type_checked_method, "bah", 9).match(
        'argument "x" is not an instance of int'
    )


def test_type_checked_classmethod(dummymodule):
    pytest.raises(
        TypeCheckError, dummymodule.DummyClass.type_checked_classmethod, "bah", 9
    ).match('argument "x" is not an instance of int')


def test_type_checked_staticmethod(dummymodule):
    pytest.raises(
        TypeCheckError, dummymodule.DummyClass.type_checked_staticmethod, "bah", 9
    ).match('argument "x" is not an instance of int')


@pytest.mark.parametrize(
    "argtype, returntype, error",
    [
        (int, str, None),
        (str, str, 'argument "x" is not an instance of str'),
        (int, int, "the return value is not an instance of int"),
    ],
    ids=["correct", "bad_argtype", "bad_returntype"],
)
def test_dynamic_type_checking_func(dummymodule, argtype, returntype, error):
    if error:
        exc = pytest.raises(
            TypeCheckError,
            dummymodule.dynamic_type_checking_func,
            4,
            argtype,
            returntype,
        )
        exc.match(error)
    else:
        assert dummymodule.dynamic_type_checking_func(4, argtype, returntype) == "4"


def test_inner_class_method(dummymodule):
    retval = dummymodule.Outer().create_inner()
    assert retval.__class__.__qualname__ == "Outer.Inner"


def test_inner_class_classmethod(dummymodule):
    retval = dummymodule.Outer.create_inner_classmethod()
    assert retval.__class__.__qualname__ == "Outer.Inner"


def test_inner_class_staticmethod(dummymodule):
    retval = dummymodule.Outer.create_inner_staticmethod()
    assert retval.__class__.__qualname__ == "Outer.Inner"


def test_contextmanager(dummymodule):
    with dummymodule.dummy_context_manager() as value:
        assert value == 1


def test_overload(dummymodule):
    dummymodule.overloaded_func(1)
    dummymodule.overloaded_func("x")
    pytest.raises(TypeCheckError, dummymodule.overloaded_func, b"foo")


def test_async_func(dummymodule):
    pytest.raises(TypeCheckError, asyncio.run, dummymodule.async_func(b"foo"))


def test_generator_valid(dummymodule):
    gen = dummymodule.generator_func(6, "foo")
    assert gen.send(None) == 6
    try:
        gen.send(None)
    except StopIteration as exc:
        assert exc.value == "foo"
    else:
        pytest.fail("Generator did not exit")


def test_generator_bad_yield_type(dummymodule):
    gen = dummymodule.generator_func("foo", "foo")
    pytest.raises(TypeCheckError, gen.send, None).match(
        "yielded value is not an instance of int"
    )
    gen.close()


def test_generator_bad_return_type(dummymodule):
    gen = dummymodule.generator_func(6, 6)
    assert gen.send(None) == 6
    pytest.raises(TypeCheckError, gen.send, None).match(
        "return value is not an instance of str"
    )
    gen.close()


def test_asyncgen_valid(dummymodule):
    gen = dummymodule.asyncgen_func(6)
    assert asyncio.run(gen.asend(None)) == 6


def test_asyncgen_bad_yield_type(dummymodule):
    gen = dummymodule.asyncgen_func("foo")
    pytest.raises(TypeCheckError, asyncio.run, gen.asend(None)).match(
        "yielded value is not an instance of int"
    )


def test_missing_return(dummymodule):
    pytest.raises(TypeCheckError, dummymodule.missing_return).match(
        "the return value is not an instance of int"
    )


def test_pep_604_union_args(dummymodule):
    pytest.raises(TypeCheckError, dummymodule.pep_604_union_args, 1.1).match(
        r'argument "x" did not match any element in the union:\n  Callable\[list, '
        r"Literal\[-1\]\]: is not callable\n  Callable\[ellipsis, Union\[int, str\]\]: "
        "is not callable"
    )


def test_pep_604_union_retval(dummymodule):
    pytest.raises(TypeCheckError, dummymodule.pep_604_union_retval, 1.1).match(
        "the return value did not match any element in the union:\n  str: is "
        "not an instance of str\n  int: is not an instance of int"
    )
