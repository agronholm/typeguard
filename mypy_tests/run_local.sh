#!/bin/bash

# For running tests with mypy that use the pypi version of typeguard we cd to
# mypy_tests so that the source code for typeguard does not appear in the search
# path.
(
    cd mypy_tests
    $@
)