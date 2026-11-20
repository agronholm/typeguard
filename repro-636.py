"""Repro for typeguard#636: ReadOnly extra_items in TypedDict aren't checked."""
from typing import Annotated
from typing_extensions import ReadOnly, TypedDict
from typeguard import check_type, TypeCheckError

class Movie(TypedDict, extra_items=ReadOnly[int]):
    title: str

class MovieAnn(TypedDict, extra_items=Annotated[ReadOnly[int], "meta"]):
    title: str

class MoviePlain(TypedDict, extra_items=int):
    title: str

# 1. issue repro: must raise now
try:
    check_type({"title": "x", "year": "nope"}, Movie)
    print("FAIL: ReadOnly[int] extra item 'nope' passed")
except TypeCheckError as e:
    print("PASS: ReadOnly[int] raised:", e)

# 2. Annotated variant: must raise now
try:
    check_type({"title": "x", "year": "nope"}, MovieAnn)
    print("FAIL: Annotated[ReadOnly[int]] extra item 'nope' passed")
except TypeCheckError as e:
    print("PASS: Annotated[ReadOnly[int]] raised:", e)

# 3. valid values still pass
check_type({"title": "x", "year": 1999}, Movie)
check_type({"title": "x", "year": 1999}, MovieAnn)
check_type({"title": "x", "year": 1999}, MoviePlain)
print("PASS: valid int extra items still pass")
