"""Module docstring."""
from __future__ import absolute_import
from __future__ import division

from typing import no_type_check, no_type_check_decorator


@no_type_check_decorator
def dummy_decorator(func):
    return func


def type_checked_func(x: int, y: int) -> int:
    return x * y


@no_type_check
def non_type_checked_func(x: int, y: str) -> 6:
    return 'foo'


@dummy_decorator
def non_type_checked_decorated_func(x: int, y: str) -> 6:
    return 'foo'


def dynamic_type_checking_func(arg, argtype, return_annotation):
    def inner(x: argtype) -> return_annotation:
        return str(x)

    return inner(arg)


class DummyClass:
    def type_checked_method(self, x: int, y: int) -> int:
        return x * y

    @classmethod
    def type_checked_classmethod(cls, x: int, y: int) -> int:
        return x * y

    @staticmethod
    def type_checked_staticmethod(x: int, y: int) -> int:
        return x * y
