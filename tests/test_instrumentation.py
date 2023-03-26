import asyncio
import sys
import warnings
from importlib import import_module
from importlib.util import cache_from_source
from pathlib import Path

import pytest
from pytest import FixtureRequest

from typeguard import TypeCheckError, config, install_import_hook

pytestmark = pytest.mark.filterwarnings("error:no type annotations present")
this_dir = Path(__file__).parent
dummy_module_path = this_dir / "dummymodule.py"
cached_module_path = Path(
    cache_from_source(str(dummy_module_path), optimization="typeguard")
)

# This block here is to test the recipe mentioned in the user guide
if "pytest" in sys.modules:
    from typeguard import typechecked
else:
    from typing import TypeVar

    _T = TypeVar("_T")

    def typechecked(target: _T, **kwargs) -> _T:
        return target if target else typechecked


@pytest.fixture(scope="module", params=["typechecked", "importhook"])
def method(request: FixtureRequest) -> str:
    return request.param


@pytest.fixture(scope="module")
def dummymodule(method: str):
    config.debug_instrumentation = True
    sys.path.insert(0, str(this_dir))
    try:
        if cached_module_path.exists():
            cached_module_path.unlink()
            sys.modules.pop("dummymodule", None)

        if method == "typechecked":
            return import_module("dummymodule")

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
        r'argument "y" \(str\) is not an instance of int'
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
        r'argument "x" \(str\) is not an instance of int'
    )


def test_type_checked_classmethod(dummymodule):
    pytest.raises(
        TypeCheckError, dummymodule.DummyClass.type_checked_classmethod, "bah", 9
    ).match(r'argument "x" \(str\) is not an instance of int')


def test_type_checked_staticmethod(dummymodule):
    pytest.raises(
        TypeCheckError, dummymodule.DummyClass.type_checked_staticmethod, "bah", 9
    ).match(r'argument "x" \(str\) is not an instance of int')


@pytest.mark.parametrize(
    "argtype, returntype, error",
    [
        (int, str, None),
        (str, str, r'argument "x" \(int\) is not an instance of str'),
        (int, int, r"the return value \(str\) is not an instance of int"),
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


@pytest.mark.xfail(reason="No workaround for this has been implemented yet")
def test_inner_class_method(dummymodule):
    retval = dummymodule.Outer().create_inner()
    assert retval.__class__.__qualname__ == "Outer.Inner"


@pytest.mark.xfail(reason="No workaround for this has been implemented yet")
def test_inner_class_classmethod(dummymodule):
    retval = dummymodule.Outer.create_inner_classmethod()
    assert retval.__class__.__qualname__ == "Outer.Inner"


@pytest.mark.xfail(reason="No workaround for this has been implemented yet")
def test_inner_class_staticmethod(dummymodule):
    retval = dummymodule.Outer.create_inner_staticmethod()
    assert retval.__class__.__qualname__ == "Outer.Inner"


def test_local_class_instance(dummymodule):
    instance = dummymodule.create_local_class_instance()
    assert (
        instance.__class__.__qualname__ == "create_local_class_instance.<locals>.Inner"
    )


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
        r"yielded value \(str\) is not an instance of int"
    )
    gen.close()


def test_generator_bad_return_type(dummymodule):
    gen = dummymodule.generator_func(6, 6)
    assert gen.send(None) == 6
    pytest.raises(TypeCheckError, gen.send, None).match(
        r"return value \(int\) is not an instance of str"
    )
    gen.close()


def test_asyncgen_valid(dummymodule):
    gen = dummymodule.asyncgen_func(6)
    assert asyncio.run(gen.asend(None)) == 6


def test_asyncgen_bad_yield_type(dummymodule):
    gen = dummymodule.asyncgen_func("foo")
    pytest.raises(TypeCheckError, asyncio.run, gen.asend(None)).match(
        r"yielded value \(str\) is not an instance of int"
    )


def test_missing_return(dummymodule):
    pytest.raises(TypeCheckError, dummymodule.missing_return).match(
        r"the return value \(None\) is not an instance of int"
    )


def test_pep_604_union_args(dummymodule):
    pytest.raises(TypeCheckError, dummymodule.pep_604_union_args, 1.1).match(
        r'argument "x" \(float\) did not match any element in the union:'
        r"\n  Callable\[list, Literal\[-1\]\]: is not callable"
        r"\n  Callable\[ellipsis, Union\[int, str\]\]: is not callable"
    )


def test_pep_604_union_retval(dummymodule):
    pytest.raises(TypeCheckError, dummymodule.pep_604_union_retval, 1.1).match(
        r"the return value \(float\) did not match any element in the union:"
        r"\n  str: is not an instance of str"
        r"\n  int: is not an instance of int"
    )


def test_paramspec(dummymodule):
    def foo(a: int, b: str, *, c: bytes) -> None:
        pass

    dummymodule.paramspec_function(foo, (1, "bar"), {"c": b"abc"})


def test_augmented_assign(dummymodule):
    assert dummymodule.aug_assign() == 2


def test_multi_assign_single_value(dummymodule):
    assert dummymodule.multi_assign_single_value() == (6, 6, 6)


def test_multi_assign_iterable(dummymodule):
    assert dummymodule.multi_assign_iterable() == ([6, 7], [6, 7], [6, 7])


def test_unpacking_assign(dummymodule):
    assert dummymodule.unpacking_assign() == (1, "foo")


def test_unpacking_assign_from_generator(dummymodule):
    assert dummymodule.unpacking_assign_generator() == (1, "foo")


def test_unpacking_assign_star_with_annotation(dummymodule):
    assert dummymodule.unpacking_assign_star_with_annotation() == (
        1,
        [b"abc", b"bah"],
        "foo",
    )


def test_unpacking_assign_star_no_annotation_success(dummymodule):
    assert dummymodule.unpacking_assign_star_no_annotation(
        (1, b"abc", b"bah", "foo")
    ) == (
        1,
        [b"abc", b"bah"],
        "foo",
    )


def test_unpacking_assign_star_no_annotation_fail(dummymodule):
    with pytest.raises(
        TypeCheckError, match=r"value assigned to z \(bytes\) is not an instance of str"
    ):
        dummymodule.unpacking_assign_star_no_annotation((1, b"abc", b"bah", b"foo"))


class TestOptionsOverride:
    def test_forward_ref_policy(self, dummymodule):
        with pytest.raises(NameError, match="name 'NonexistentType' is not defined"):
            dummymodule.override_forward_ref_policy(6)

    def test_typecheck_fail_callback(self, dummymodule, capsys):
        dummymodule.override_typecheck_fail_callback("foo")
        assert capsys.readouterr().out == (
            'argument "value" (str) is not an instance of int\n'
        )

    def test_override_collection_check_strategy(self, dummymodule):
        with pytest.raises(
            TypeCheckError,
            match=r'item 1 of argument "value" \(list\) is not an instance of int',
        ):
            dummymodule.override_collection_check_strategy([1, "foo"])

    def test_outer_class_typecheck_fail_callback(self, dummymodule, capsys):
        dummymodule.OverrideClass().override_typecheck_fail_callback("foo")
        assert capsys.readouterr().out == (
            'argument "value" (str) is not an instance of int\n'
        )

    def test_inner_class_no_overrides(self, dummymodule):
        with pytest.raises(TypeCheckError):
            dummymodule.OverrideClass.Inner().override_typecheck_fail_callback("foo")
