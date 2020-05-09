import sys
import warnings
import importlib
from importlib.util import cache_from_source
from pathlib import Path

import pytest

from typeguard.importhook import install_import_hook

this_dir = Path(__file__).parent
dummy_module_path = this_dir / 'dummymodule.py'
cached_module_path = Path(cache_from_source(str(dummy_module_path), optimization='typeguard'))


def import_fixtures_module(module_name):
    if cached_module_path.exists():
        cached_module_path.unlink()

    sys.path.insert(0, str(this_dir))

    try:
        with install_import_hook(module_name):
            with warnings.catch_warnings():
                warnings.filterwarnings('error', module='typeguard')

                if module_name not in sys.modules:
                    module = importlib.import_module(module_name)
                else:
                    module = importlib.reload(sys.modules[module_name])

                return module
    finally:
        sys.path.remove(str(this_dir))


@pytest.fixture(scope='module')
def dummymodule():
    return import_fixtures_module('dummymodule')


def test_cached_module(dummymodule):
    assert cached_module_path.is_file()


def test_type_checked_func(dummymodule):
    assert dummymodule.type_checked_func(2, 3) == 6


def test_type_checked_func_error(dummymodule):
    pytest.raises(TypeError, dummymodule.type_checked_func, 2, '3').\
        match('"y" must be int; got str instead')


def test_non_type_checked_func(dummymodule):
    assert dummymodule.non_type_checked_func('bah', 9) == 'foo'


def test_non_type_checked_decorated_func(dummymodule):
    assert dummymodule.non_type_checked_decorated_func('bah', 9) == 'foo'


def test_type_checked_method(dummymodule):
    instance = dummymodule.DummyClass()
    pytest.raises(TypeError, instance.type_checked_method, 'bah', 9).\
        match('"x" must be int; got str instead')


def test_type_checked_classmethod(dummymodule):
    pytest.raises(TypeError, dummymodule.DummyClass.type_checked_classmethod, 'bah', 9).\
        match('"x" must be int; got str instead')


def test_type_checked_staticmethod(dummymodule):
    pytest.raises(TypeError, dummymodule.DummyClass.type_checked_classmethod, 'bah', 9).\
        match('"x" must be int; got str instead')


@pytest.mark.parametrize('argtype, returntype, error', [
    (int, str, None),
    (str, str, '"x" must be str; got int instead'),
    (int, int, 'type of the return value must be int; got str instead')
], ids=['correct', 'bad_argtype', 'bad_returntype'])
def test_dynamic_type_checking_func(dummymodule, argtype, returntype, error):
    if error:
        exc = pytest.raises(TypeError, dummymodule.dynamic_type_checking_func, 4, argtype,
                            returntype)
        exc.match(error)
    else:
        assert dummymodule.dynamic_type_checking_func(4, argtype, returntype) == '4'


def test_class_in_function(dummymodule):
    create_inner = dummymodule.outer()
    retval = create_inner()
    assert retval.__class__.__qualname__ == 'outer.<locals>.Inner'


def test_inner_class_method(dummymodule):
    retval = dummymodule.Outer().create_inner()
    assert retval.__class__.__qualname__ == 'Outer.Inner'


def test_inner_class_classmethod(dummymodule):
    retval = dummymodule.Outer.create_inner_classmethod()
    assert retval.__class__.__qualname__ == 'Outer.Inner'


def test_inner_class_staticmethod(dummymodule):
    retval = dummymodule.Outer.create_inner_staticmethod()
    assert retval.__class__.__qualname__ == 'Outer.Inner'


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_check_module_annotations_successed():
    import_fixtures_module('dummymodule_3_6')


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_check_module_annotations_failed(monkeypatch):
    monkeypatch.setenv('TYPEGUARD_TEST_WRONG_ANNOTATION', 'True')

    exc = pytest.raises(TypeError, import_fixtures_module, 'dummymodule_3_6')
    exc.match('type of wrong_annotated_attribute must be int; got float instead')
