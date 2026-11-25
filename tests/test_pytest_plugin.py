from textwrap import dedent

import pytest
from pytest import MonkeyPatch, Pytester

from typeguard import CollectionCheckStrategy, ForwardRefPolicy, TypeCheckConfiguration


@pytest.fixture
def config(monkeypatch: MonkeyPatch) -> TypeCheckConfiguration:
    config = TypeCheckConfiguration()
    monkeypatch.setattr("typeguard._pytest_plugin.global_config", config)
    return config


def test_config_options(pytester: Pytester, config: TypeCheckConfiguration) -> None:
    pytester.makepyprojecttoml(
        '''
        [tool.pytest.ini_options]
        typeguard-packages = """
        mypackage
        otherpackage"""
        typeguard-debug-instrumentation = true
        typeguard-typecheck-fail-callback = "mypackage:failcallback"
        typeguard-forward-ref-policy = "ERROR"
        typeguard-collection-check-strategy = "ALL_ITEMS"
        '''
    )
    pytester.makepyfile(
        mypackage=(
            dedent(
                """
            def failcallback():
                pass
            """
            )
        )
    )

    pytester.plugins = ["typeguard"]
    pytester.syspathinsert()
    pytestconfig = pytester.parseconfigure()
    assert pytestconfig.getini("typeguard-packages") == ["mypackage", "otherpackage"]
    assert config.typecheck_fail_callback.__name__ == "failcallback"
    assert config.debug_instrumentation is True
    assert config.forward_ref_policy is ForwardRefPolicy.ERROR
    assert config.collection_check_strategy is CollectionCheckStrategy.ALL_ITEMS


def test_commandline_options(
    pytester: Pytester, config: TypeCheckConfiguration
) -> None:
    pytester.makepyfile(
        mypackage=(
            dedent(
                """
            def failcallback():
                pass
            """
            )
        )
    )

    pytester.plugins = ["typeguard"]
    pytester.syspathinsert()
    pytestconfig = pytester.parseconfigure(
        "--typeguard-packages=mypackage,otherpackage",
        "--typeguard-typecheck-fail-callback=mypackage:failcallback",
        "--typeguard-debug-instrumentation",
        "--typeguard-forward-ref-policy=ERROR",
        "--typeguard-collection-check-strategy=ALL_ITEMS",
    )
    assert pytestconfig.getoption("typeguard_packages") == "mypackage,otherpackage"
    assert config.typecheck_fail_callback.__name__ == "failcallback"
    assert config.debug_instrumentation is True
    assert config.forward_ref_policy is ForwardRefPolicy.ERROR
    assert config.collection_check_strategy is CollectionCheckStrategy.ALL_ITEMS


def test_config_options_with_ignore(pytester: Pytester) -> None:
    pytester.makepyprojecttoml(
        '''
        [tool.pytest.ini_options]
        typeguard-packages = """
        ham
        spam.eggs"""
        typeguard-packages-ignore = """
        ham.ignoreme
        spam.eggs.ignoretoo"""
        '''
    )

    pytester.plugins = ["typeguard"]
    pytester.syspathinsert()
    pytestconfig = pytester.parseconfigure()
    assert pytestconfig.getini("typeguard-packages") == ["ham", "spam.eggs"]
    assert pytestconfig.getini("typeguard-packages-ignore") == [
        "ham.ignoreme",
        "spam.eggs.ignoretoo",
    ]


def test_commandline_options_with_ignore(pytester: Pytester) -> None:
    pytester.plugins = ["typeguard"]
    pytester.syspathinsert()
    pytestconfig = pytester.parseconfigure(
        "--typeguard-packages=ham,spam.eggs",
        "--typeguard-packages-ignore=ham.ignoreme,spam.eggs.ignoretoo",
    )
    assert pytestconfig.getoption("typeguard_packages") == "ham,spam.eggs"
    assert (
        pytestconfig.getoption("typeguard_packages_ignore")
        == "ham.ignoreme,spam.eggs.ignoretoo"
    )


def test_typechecked_preserves_assertion_rewriting(pytester: Pytester) -> None:
    """Regression test for #477: assertion introspection must survive @typechecked."""
    pytester.makepyfile(
        """
        from typeguard import typechecked

        @typechecked
        def test_example() -> None:
            result = 1
            assert result == 2
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*assert 1 == 2*"])


def test_typechecked_still_checks_in_rewritten_module(pytester: Pytester) -> None:
    pytester.makepyfile(
        """
        from typeguard import TypeCheckError, typechecked

        @typechecked
        def add(a: int, b: int) -> int:
            return a + b

        @typechecked
        def bad_return() -> int:
            return "nope"

        def test_ok() -> None:
            assert add(1, 2) == 3

        def test_bad_argument() -> None:
            try:
                add("x", 2)
            except TypeCheckError as exc:
                assert 'argument "a"' in str(exc)
            else:
                raise AssertionError("no TypeCheckError raised")

        def test_bad_return() -> None:
            try:
                bad_return()
            except TypeCheckError:
                pass
            else:
                raise AssertionError("no TypeCheckError raised")
        """
    )
    result = pytester.runpytest("-q")
    result.assert_outcomes(passed=3)
