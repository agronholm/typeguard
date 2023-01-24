"""
Transforms lazily evaluated PEP 604 unions into typing.Unions, for compatibility with
Python versions older than 3.10.
"""

from lark import Lark, Transformer


class UnionTransformer(Transformer):
    def typ(self, children):
        return "".join(children)

    def pep604_union(self, children):
        return "Union[" + ", ".join(children) + "]"

    def qualification(self, children):
        return "[" + ", ".join(children) + "]"

    def string(self, children):
        return children[0].value

    def name(self, children):
        return children[0].value

    def ellipsis(self, _):
        return "..."

    def number(self, children):
        if len(children) == 2:  # minus sign
            return f"-{children[1].value}"
        else:
            return str(children[0].value)


HINT_PARSER = Lark(
    """
    ?hint: pep604_union | typ
    pep604_union: typ ("|" typ)+

    typ: name (qualification)? | qualification | number | string | ellipsis
    qualification: "[" hint ("," hint)* "]" | "[]"
    number: (minus)? (DEC_NUMBER | HEX_NUMBER | BIN_NUMBER | OCT_NUMBER)
    ?minus: "-"
    ellipsis: "..."

    %import python.name
    %import python.string
    %import python.DEC_NUMBER
    %import python.HEX_NUMBER
    %import python.BIN_NUMBER
    %import python.OCT_NUMBER
    %import common.WS
    %ignore WS
    """,
    start="hint",
)


def translate_type_hint(hint: str) -> str:
    tree = HINT_PARSER.parse(hint)
    return UnionTransformer(tree).transform(tree)
