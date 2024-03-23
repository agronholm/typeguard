from typing import (
    AbstractSet,
    Collection,
    Dict,
    Generic,
    List,
    NamedTuple,
    NewType,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

T_Foo = TypeVar("T_Foo")

TBound = TypeVar("TBound", bound="Parent")
TConstrained = TypeVar("TConstrained", "Parent", int)
TTypingConstrained = TypeVar("TTypingConstrained", List[int], AbstractSet[str])
TIntStr = TypeVar("TIntStr", int, str)
TIntCollection = TypeVar("TIntCollection", int, Collection[int])
TParent = TypeVar("TParent", bound="Parent")
TChild = TypeVar("TChild", bound="Child")


class Employee(NamedTuple):
    name: str
    id: int


JSONType = Union[str, float, bool, None, List["JSONType"], Dict[str, "JSONType"]]
myint = NewType("myint", int)
mylist = NewType("mylist", List[int])


class FooGeneric(Generic[T_Foo]):
    pass


class Parent:
    pass


class Child(Parent):
    def method(self, a: int) -> None:
        pass


class StaticProtocol(Protocol):
    def meth(self) -> None: ...


@runtime_checkable
class RuntimeProtocol(Protocol):
    member: int

    def meth(self) -> None: ...
