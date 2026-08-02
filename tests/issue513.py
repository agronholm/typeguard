from typing import Annotated

from typeguard import typechecked

annotation_map = {"a b": int}
MyAnnotated = Annotated


@typechecked
def annotated_by_string_key(x: annotation_map["a b"]) -> int:  # noqa: F722
    return x


@typechecked
def aliased_annotated(x: MyAnnotated[int, "a b"]) -> int:  # noqa: F722
    return x
