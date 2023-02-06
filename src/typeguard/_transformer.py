from __future__ import annotations

from ast import (
    Assign,
    AsyncFunctionDef,
    Attribute,
    Call,
    ClassDef,
    Constant,
    Expr,
    FunctionDef,
    Import,
    ImportFrom,
    Load,
    Module,
    Name,
    NodeTransformer,
    Pass,
    Return,
    Store,
    Str,
    Yield,
    alias,
    copy_location,
    fix_missing_locations,
)
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

generator_names = (
    "typing.Generator",
    "collections.abc.Generator",
    "typing.Iterator",
    "collections.abc.Iterator",
    "typing.Iterable",
    "collections.abc.Iterable",
    "typing.AsyncIterator",
    "collections.abc.AsyncIterator",
    "typing.AsyncIterable",
    "collections.abc.AsyncIterable",
    "typing.AsyncGenerator",
    "collections.abc.AsyncGenerator",
)
anytype_names = (
    "typing.Any",
    "typing_extensions.Any",
)


@dataclass
class TransformMemo:
    node: ClassDef | FunctionDef | AsyncFunctionDef | None
    parent: TransformMemo | None
    path: tuple[str, ...]
    return_annotation: Expr | None = None
    is_async: bool = False
    local_names: set[str] = field(init=False, default_factory=set)
    any_names: set[str] = field(init=False, default_factory=set)
    typing_module_names: set[str] = field(init=False, default_factory=set)
    typeguard_module_name: str | None = field(init=False, default=None)
    typechecked_import_name: str | None = field(init=False, default=None)
    load_names: dict[str, Name] = field(init=False, default_factory=dict)
    store_names: dict[str, Name] = field(init=False, default_factory=dict)
    has_yield_expressions: bool = field(init=False, default=False)
    has_return_expressions: bool = field(init=False, default=False)
    call_memo_name: Name | None = field(init=False, default=None)
    should_instrument: bool = field(init=False, default=True)

    def get_unused_name(self, name: str) -> str:
        while True:
            if self.parent:
                name = self.parent.get_unused_name(name)

            if name not in self.local_names:
                break

            name += "_"

        self.local_names.add(name)
        return name

    def get_call_memo_name(self) -> Name:
        if not self.call_memo_name:
            self.call_memo_name = Name(id="call_memo", ctx=Load())

        return self.call_memo_name

    def get_typeguard_import(self, name: str) -> Name:
        if name in self.load_names:
            return self.load_names[name]

        alias = self.get_unused_name(name)
        node = self.load_names[name] = Name(id=alias, ctx=Load())
        self.store_names[name] = Name(id=alias, ctx=Store())
        return node

    def insert_typeguard_imports(
        self, node: Module | FunctionDef | AsyncFunctionDef
    ) -> None:
        if not self.load_names:
            return

        # Insert "from typeguard import ..." after any "from __future__ ..." imports
        for i, child in enumerate(node.body):
            if isinstance(child, ImportFrom) and child.module == "__future__":
                continue
            elif isinstance(child, Expr) and isinstance(child.value, Str):
                continue  # module docstring
            else:
                aliases = [
                    alias(orig_name, new_name.id if orig_name != new_name.id else None)
                    for orig_name, new_name in sorted(self.load_names.items())
                ]
                node.body.insert(i, ImportFrom("typeguard", aliases, 0))
                break

    def is_any(self, annotation: Expr | None) -> bool:
        if annotation is None:
            return False

        # Check for "Any"
        if isinstance(annotation, Name) and annotation.id in self.any_names:
            return True

        # Check for "typing.Any" and "typing_extensions.Any"
        if (
            isinstance(annotation, Attribute)
            and isinstance(annotation, Name)
            and annotation.value.id in self.typing_module_names
            and annotation.attr == "Any"
        ):
            return True

        if self.parent:
            return self.parent.is_any(annotation)

        return False


class TypeguardTransformer(NodeTransformer):
    def __init__(self, target_path: Sequence[str] | None = None) -> None:
        self._target_path = tuple(target_path) if target_path else None
        self._memo = self._module_memo = TransformMemo(None, None, ())

    @contextmanager
    def _use_memo(
        self, node: Module | ClassDef | FunctionDef
    ) -> Generator[None, Any, None]:
        new_memo = TransformMemo(node, self._memo, self._memo.path + (node.name,))
        if isinstance(node, (FunctionDef, AsyncFunctionDef)):
            new_memo.return_annotation = node.returns
            new_memo.should_instrument = (
                self._target_path is None or new_memo.path == self._target_path
            )

        if isinstance(node, AsyncFunctionDef):
            new_memo.is_async = True

        old_memo = self._memo
        self._memo = new_memo
        yield
        self._memo = old_memo

    def _get_typeguard_import(self, name: str) -> Name:
        memo = self._memo if self._target_path else self._module_memo
        return memo.get_typeguard_import(name)

    def visit_Name(self, node: Name) -> Name:
        self._memo.local_names.add(node.id)
        return node

    def visit_Module(self, node: Module) -> Module:
        self.generic_visit(node)
        self._memo.insert_typeguard_imports(node)

        fix_missing_locations(node)
        return node

    def visit_Import(self, node: Import) -> Import:
        for name in node.names:
            self._memo.local_names.add(name.asname or name.name)
            if name.name == "typeguard":
                self._memo.typeguard_module_name = name.asname or name.name
            elif name.name in ("typing", "typing_extensions"):
                self._memo.typing_module_names.add(name.asname or name.name)

        return node

    def visit_ImportFrom(self, node: ImportFrom) -> ImportFrom:
        for name in node.names:
            self._memo.local_names.add(name.asname or name.name)
            if node.module == "typeguard":
                if name.name == "typechecked":
                    self._memo.typechecked_import_name = name.asname or name.name
            elif node.module in ("typing", "typing_extensions"):
                if name.name == "Any":
                    self._memo.any_names.add(name.asname or name.name)

        return node

    def visit_ClassDef(self, node: ClassDef) -> ClassDef | None:
        self._memo.local_names.add(node.name)

        # Eliminate top level classes not belonging to the target path
        if (
            self._target_path is not None
            and not self._memo.path
            and node.name != self._target_path[0]
        ):
            return None

        with self._use_memo(node):
            self.generic_visit(node)
            return node

    def visit_FunctionDef(
        self, node: FunctionDef | AsyncFunctionDef
    ) -> FunctionDef | AsyncFunctionDef | None:
        self._memo.local_names.add(node.name)

        # Eliminate top level functions not belonging to the target path
        if (
            self._target_path is not None
            and not self._memo.path
            and node.name != self._target_path[0]
        ):
            return None

        with self._use_memo(node):
            self.generic_visit(node)

            if self._target_path is None or self._memo.path == self._target_path:
                has_annotated_args = any(
                    arg.annotation and not self._memo.is_any(arg.annotation)
                    for arg in node.args.args
                )
                has_annotated_return = bool(node.returns) and not self._memo.is_any(
                    node.returns
                )

                if has_annotated_args:
                    func_name = self._get_typeguard_import("check_argument_types")
                    node.body.insert(
                        0,
                        Expr(
                            Call(
                                func_name,
                                [self._memo.get_call_memo_name()],
                                [],
                            )
                        ),
                    )

                # Add a checked "return None" to the end if there's no explicit return
                # Skip if the return annotation is None or Any
                if not self._memo.is_async or not self._memo.has_yield_expressions:
                    if has_annotated_return and not isinstance(node.body[-1], Return):
                        if (
                            not isinstance(self._memo.return_annotation, Constant)
                            or self._memo.return_annotation.value is not None
                        ):
                            func_name = self._get_typeguard_import("check_return_type")
                            return_node = Return(
                                Call(
                                    func_name,
                                    [
                                        Constant(None),
                                        self._memo.get_call_memo_name(),
                                    ],
                                    [],
                                )
                            )

                            # Replace a placeholder "pass" at the end
                            if isinstance(node.body[-1], Pass):
                                copy_location(return_node, node.body[-1])
                                del node.body[-1]

                            node.body.append(return_node)

                # Insert code to create the call memo, if it was ever needed for this
                # function
                if self._memo.call_memo_name:
                    extra_args: list[expr] = []
                    if self._memo.parent and isinstance(
                        self._memo.parent.node, ClassDef
                    ):
                        for expr in node.decorator_list:
                            if isinstance(expr, Name) and expr.id == "staticmethod":
                                break
                            elif isinstance(expr, Name) and expr.id == "classmethod":
                                extra_args.append(
                                    Name(id=node.args.args[0].arg, ctx=Load())
                                )
                                break
                        else:
                            if node.args.args:
                                extra_args.append(
                                    Attribute(
                                        Name(id=node.args.args[0].arg, ctx=Load()),
                                        "__class__",
                                        ctx=Load(),
                                    )
                                )

                    # Construct the function reference
                    # Nested functions get special treatment: the function name is added
                    # to free variables (and the closure of the resulting function)
                    func_reference: expr = Name(id=node.name, ctx=Load())
                    previous_attribute: Attribute | None = None
                    parent_memo = self._memo.parent
                    while parent_memo:
                        if isinstance(
                            parent_memo.node, (FunctionDef, AsyncFunctionDef)
                        ):
                            # This is a nested function. Use the function name as-is.
                            func_reference = Name(id=node.name, ctx=Load())
                            break
                        elif not isinstance(parent_memo.node, ClassDef):
                            break

                        attrname = (
                            previous_attribute.value.id
                            if previous_attribute
                            else func_reference.id
                        )
                        attribute = Attribute(
                            Name(id=parent_memo.node.name, ctx=Load()),
                            attrname,
                            ctx=Load(),
                        )
                        if previous_attribute is None:
                            func_reference = attribute
                        else:
                            previous_attribute.value = attribute

                        previous_attribute = attribute
                        parent_memo = parent_memo.parent

                    self._memo.call_memo_name.id = self._memo.get_unused_name(
                        "call_memo"
                    )
                    call_memo_store_name = Name(
                        id=self._memo.call_memo_name.id, ctx=Store()
                    )
                    locals_call = Call(Name(id="locals", ctx=Load()), [], [])
                    memo_expr = Call(
                        self._get_typeguard_import("CallMemo"),
                        [func_reference, locals_call, *extra_args],
                        [],
                    )
                    node.body.insert(
                        0,
                        Assign([call_memo_store_name], memo_expr),
                    )

                    self._memo.insert_typeguard_imports(node)

                    # Rmove any placeholder "pass" at the end
                    if isinstance(node.body[-1], Pass):
                        del node.body[-1]

        return node

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef):
        self.visit_FunctionDef(node)
        return node

    def visit_Return(self, node: Return):
        self.generic_visit(node)
        if (
            self._memo.should_instrument
            and self._memo.return_annotation
            and not self._memo.is_any(self._memo.return_annotation)
        ):
            func_name = self._get_typeguard_import("check_return_type")
            old_node = node
            retval = old_node.value or Constant(None)
            node = Return(
                Call(
                    func_name,
                    [retval, self._memo.get_call_memo_name()],
                    [],
                )
            )
            copy_location(node, old_node)

        return node

    def visit_Yield(self, node: Yield):
        self._memo.has_yield_expressions = True
        self.generic_visit(node)
        if (
            self._memo.should_instrument
            and self._memo.return_annotation
            and not self._memo.is_any(self._memo.return_annotation)
        ):
            func_name = self._get_typeguard_import("check_yield_type")
            yieldval = node.value or Constant(None)
            node.value = Call(
                func_name,
                [yieldval, self._memo.get_call_memo_name()],
                [],
            )

            func_name = self._get_typeguard_import("check_send_type")
            old_node = node
            node = Call(
                func_name,
                [old_node, self._memo.get_call_memo_name()],
                [],
            )
            copy_location(node, old_node)

        return node
