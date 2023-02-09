import sys
import warnings
from importlib import import_module
from importlib.util import cache_from_source
from pathlib import Path

import pytest
from pytest import FixtureRequest

from typeguard import TypeCheckError
from typeguard.importhook import TypeguardFinder, install_import_hook

pytestmark = pytest.mark.filterwarnings("error:no type annotations present")
this_dir = Path(__file__).parent
dummy_module_path = this_dir / "dummymodule.py"
cached_module_path = Path(
    cache_from_source(str(dummy_module_path), optimization="typeguard")
)


@pytest.fixture(scope="module")
def dummymodule(request: FixtureRequest):
    packages = getattr(request, "param", ["dummymodule"])
    if cached_module_path.exists():
        cached_module_path.unlink()

    sys.path.insert(0, str(this_dir))
    try:
        with install_import_hook(packages):
            with warnings.catch_warnings():
                warnings.filterwarnings("error", module="typeguard")
                module = import_module("dummymodule")
                return module
    finally:
        sys.path.remove(str(this_dir))


@pytest.mark.parametrize("dummymodule", [None], indirect=True)
def test_blanket_import(dummymodule):
    try:
        pytest.raises(TypeCheckError, dummymodule.type_checked_func, 2, "3").match(
            'argument "y" is not an instance of int'
        )
    finally:
        del sys.modules["dummymodule"]


def test_package_name_matching():
    """
    The path finder only matches configured (sub)packages.
    """
    packages = ["ham", "spam.eggs"]
    dummy_original_pathfinder = None
    finder = TypeguardFinder(packages, dummy_original_pathfinder)

    assert finder.should_instrument("ham")
    assert finder.should_instrument("ham.eggs")
    assert finder.should_instrument("spam.eggs")

    assert not finder.should_instrument("spam")
    assert not finder.should_instrument("ha")
    assert not finder.should_instrument("spam_eggs")
