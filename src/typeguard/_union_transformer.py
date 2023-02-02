"""
Transforms lazily evaluated PEP 604 unions into typing.Unions, for compatibility with
Python versions older than 3.10.
"""
from __future__ import annotations

from ast import (
    BinOp,
    Index,
    Load,
    Name,
    NodeTransformer,
    Subscript,
    Tuple,
    fix_missing_locations,
    parse,
)
from types import CodeType
from typing import Any, Dict, FrozenSet, List, Set, Union

type_substitutions = {
    "dict": Dict,
    "list": List,
    "tuple": Tuple,
    "set": Set,
    "frozenset": FrozenSet,
    "Union": Union,
}


class UnionTransformer(NodeTransformer):
    def visit_BinOp(self, node: BinOp) -> Any:
        self.generic_visit(node)
        return Subscript(
            value=Name(id="Union", ctx=Load()),
            slice=Index(Tuple(elts=[node.left, node.right], ctx=Load()), ctx=Load()),
            ctx=Load(),
        )


def compile_type_hint(hint: str) -> CodeType:
    parsed = parse(hint, "<string>", "eval")
    UnionTransformer().visit(parsed)
    fix_missing_locations(parsed)
    return compile(parsed, "<string>", "eval")
