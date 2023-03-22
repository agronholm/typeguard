from __future__ import annotations

import sys
from _ast import List
from ast import (
    Add,
    AnnAssign,
    Assign,
    AsyncFunctionDef,
    Attribute,
    AugAssign,
    BinOp,
    BitAnd,
    BitOr,
    BitXor,
    Call,
    ClassDef,
    Constant,
    Dict,
    Div,
    Expr,
    FloorDiv,
    FunctionDef,
    If,
    Import,
    ImportFrom,
    Index,
    Load,
    LShift,
    MatMult,
    Mod,
    Module,
    Mult,
    Name,
    NodeTransformer,
    NodeVisitor,
    Pass,
    Pow,
    Return,
    RShift,
    Starred,
    Store,
    Str,
    Sub,
    Subscript,
    Tuple,
    Yield,
    YieldFrom,
    alias,
    copy_location,
    expr,
    fix_missing_locations,
    walk,
)
from collections import defaultdict
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

if sys.version_info < (3, 10):
    from ._union_transformer import UnionTransformer
else:
    UnionTransformer = None

if sys.version_info >= (3, 8):
    from ast import NamedExpr

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
ignore_decorators = (
    "typing.no_type_check",
    "typeguard.typeguard_ignore",
)
aug_assign_functions = {
    Add: "iadd",
    Sub: "isub",
    Mult: "imul",
    MatMult: "imatmul",
    Div: "itruediv",
    FloorDiv: "ifloordiv",
    Mod: "imod",
    Pow: "ipow",
    LShift: "ilshift",
    RShift: "irshift",
    BitAnd: "iand",
    BitXor: "ixor",
    BitOr: "ior",
}


@dataclass
class TransformMemo:
    node: Module | ClassDef | FunctionDef | AsyncFunctionDef | None
    parent: TransformMemo | None
    path: tuple[str, ...]
    return_annotation: expr | None = None
    yield_annotation: expr | None = None
    send_annotation: expr | None = None
    is_async: bool = False
    local_names: set[str] = field(init=False, default_factory=set)
    imported_names: dict[str, str] = field(init=False, default_factory=dict)
    ignored_names: set[str] = field(init=False, default_factory=set)
    load_names: defaultdict[str, dict[str, Name]] = field(
        init=False, default_factory=lambda: defaultdict(dict)
    )
    has_yield_expressions: bool = field(init=False, default=False)
    has_return_expressions: bool = field(init=False, default=False)
    call_memo_name: Name | None = field(init=False, default=None)
    should_instrument: bool = field(init=False, default=True)
    variable_annotations: dict[str, expr] = field(init=False, default_factory=dict)

    def get_unused_name(self, name: str) -> str:
        memo: TransformMemo | None = self
        while memo is not None:
            if name in memo.local_names:
                memo = self
                name += "_"
            else:
                memo = memo.parent

        self.local_names.add(name)
        return name

    def is_ignored_name(self, expression: expr | Expr | None) -> bool:
        top_expression = (
            expression.value if isinstance(expression, Expr) else expression
        )

        if isinstance(top_expression, Attribute) and isinstance(
            top_expression.value, Name
        ):
            name = top_expression.value.id
        elif isinstance(top_expression, Name):
            name = top_expression.id
        else:
            return False

        memo: TransformMemo | None = self
        while memo is not None:
            if name in memo.ignored_names:
                return True

            memo = memo.parent

        return False

    def get_call_memo_name(self) -> Name:
        if not self.call_memo_name:
            self.call_memo_name = Name(id="call_memo", ctx=Load())

        return self.call_memo_name

    def get_import(self, module: str, name: str) -> Name:
        module_names = self.load_names[module]
        if name in module_names:
            return module_names[name]

        alias = self.get_unused_name(name)
        node = module_names[name] = Name(id=alias, ctx=Load())
        return node

    def insert_imports(self, node: Module | FunctionDef | AsyncFunctionDef) -> None:
        """Insert imports needed by injected code."""
        if not self.load_names:
            return

        # Insert imports after any "from __future__ ..." imports and any docstring
        for i, child in enumerate(node.body):
            if isinstance(child, ImportFrom) and child.module == "__future__":
                continue
            elif isinstance(child, Expr) and isinstance(child.value, Str):
                continue  # module docstring

            for modulename, names in self.load_names.items():
                aliases = [
                    alias(orig_name, new_name.id if orig_name != new_name.id else None)
                    for orig_name, new_name in sorted(names.items())
                ]
                node.body.insert(i, ImportFrom(modulename, aliases, 0))

            break

    def name_matches(self, expression: expr | Expr | None, *names: str) -> bool:
        if expression is None:
            return False

        path: list[str] = []
        top_expression = (
            expression.value if isinstance(expression, Expr) else expression
        )

        if isinstance(top_expression, Subscript):
            top_expression = top_expression.value

        while isinstance(top_expression, Attribute):
            path.insert(0, top_expression.attr)
            top_expression = top_expression.value

        if not isinstance(top_expression, Name):
            return False

        translated = self.imported_names.get(top_expression.id, top_expression.id)
        path.insert(0, translated)
        joined_path = ".".join(path)
        if joined_path in names:
            return True
        elif self.parent:
            return self.parent.name_matches(expression, *names)
        else:
            return False


class NameCollector(NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Import(self, node: Import) -> None:
        for name in node.names:
            self.names.add(name.asname or name.name)

    def visit_ImportFrom(self, node: ImportFrom) -> None:
        for name in node.names:
            self.names.add(name.asname or name.name)

    def visit_Assign(self, node: Assign) -> None:
        for target in node.targets:
            if isinstance(target, Name):
                self.names.add(target.id)

    def visit_NamedExpr(self, node: NamedExpr) -> Any:
        if isinstance(node.target, Name):
            self.names.add(node.target.id)

    def visit_FunctionDef(self, node: FunctionDef) -> None:
        pass

    def visit_ClassDef(self, node: ClassDef) -> None:
        pass


class GeneratorDetector(NodeVisitor):
    """Detects if a function node is a generator function."""

    contains_yields: bool = False
    in_root_function: bool = False

    def visit_Yield(self, node: Yield) -> Any:
        self.contains_yields = True

    def visit_YieldFrom(self, node: YieldFrom) -> Any:
        self.contains_yields = True

    def visit_ClassDef(self, node: ClassDef) -> Any:
        pass

    def visit_FunctionDef(self, node: FunctionDef | AsyncFunctionDef) -> Any:
        if not self.in_root_function:
            self.in_root_function = True
            self.generic_visit(node)
            self.in_root_function = False

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef) -> Any:
        self.visit_FunctionDef(node)


class TypeguardTransformer(NodeTransformer):
    def __init__(self, target_path: Sequence[str] | None = None) -> None:
        self._target_path = tuple(target_path) if target_path else None
        self._memo = self._module_memo = TransformMemo(None, None, ())

    @contextmanager
    def _use_memo(
        self, node: ClassDef | FunctionDef | AsyncFunctionDef
    ) -> Generator[None, Any, None]:
        new_memo = TransformMemo(node, self._memo, self._memo.path + (node.name,))
        if isinstance(node, (FunctionDef, AsyncFunctionDef)):
            new_memo.should_instrument = (
                self._target_path is None or new_memo.path == self._target_path
            )
            if new_memo.should_instrument:
                # Check if the function is a generator function
                detector = GeneratorDetector()
                detector.visit(node)

                # Extract yield, send and return types where possible from a subscripted
                # annotation like Generator[int, str, bool]
                if detector.contains_yields and new_memo.name_matches(
                    node.returns, *generator_names
                ):
                    if isinstance(node.returns, Subscript):
                        annotation_slice = node.returns.slice

                        # Python < 3.9
                        if isinstance(annotation_slice, Index):
                            annotation_slice = (
                                annotation_slice.value  # type: ignore[attr-defined]
                            )

                        if isinstance(annotation_slice, Tuple):
                            items = annotation_slice.elts
                        else:
                            items = [annotation_slice]

                        if len(items) > 0:
                            new_memo.yield_annotation = items[0]

                        if len(items) > 1:
                            new_memo.send_annotation = items[1]

                        if len(items) > 2:
                            new_memo.return_annotation = items[2]
                else:
                    new_memo.return_annotation = node.returns

        if isinstance(node, AsyncFunctionDef):
            new_memo.is_async = True

        old_memo = self._memo
        self._memo = new_memo
        yield
        self._memo = old_memo

    def _get_import(self, module: str, name: str) -> Name:
        memo = self._memo if self._target_path else self._module_memo
        return memo.get_import(module, name)

    def visit_Name(self, node: Name) -> Name:
        self._memo.local_names.add(node.id)
        return node

    def visit_Module(self, node: Module) -> Module:
        self.generic_visit(node)
        self._memo.insert_imports(node)

        fix_missing_locations(node)
        return node

    def visit_Import(self, node: Import) -> Import:
        for name in node.names:
            self._memo.local_names.add(name.asname or name.name)
            self._memo.imported_names[name.asname or name.name] = name.name

        return node

    def visit_ImportFrom(self, node: ImportFrom) -> ImportFrom:
        for name in node.names:
            if name.name != "*":
                alias = name.asname or name.name
                self._memo.local_names.add(alias)
                self._memo.imported_names[alias] = f"{node.module}.{name.name}"

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
        """
        Injects type checks for function arguments, and for a return of None if the
        function is annotated to return something else than Any or None, and the body
        ends without an explicit "return".

        """
        self._memo.local_names.add(node.name)

        # Eliminate top level functions not belonging to the target path
        if (
            self._target_path is not None
            and not self._memo.path
            and node.name != self._target_path[0]
        ):
            return None

        for decorator in node.decorator_list.copy():
            if self._memo.name_matches(decorator, "typing.overload"):
                # Remove overloads entirely
                return None
            elif self._memo.name_matches(decorator, "typeguard.typechecked"):
                # Remove @typechecked decorators to prevent duplicate instrumentation
                node.decorator_list.remove(decorator)

        # Skip instrumentation if we're instrumenting the whole module and the function
        # contains either @no_type_check or @typeguard_ignore
        if self._target_path is None:
            for decorator in node.decorator_list:
                if self._memo.name_matches(decorator, *ignore_decorators):
                    return node

        # Eliminate annotations that were imported inside an "if TYPE_CHECKED:" block
        for argument in node.args.args:
            if self._memo.is_ignored_name(argument.annotation):
                argument.annotation = None

        with self._use_memo(node):
            if self._target_path is None or self._memo.path == self._target_path:
                all_args = node.args.args + node.args.kwonlyargs
                if sys.version_info >= (3, 8):
                    all_args.extend(node.args.posonlyargs)

                arg_annotations = {
                    arg.arg: arg.annotation
                    for arg in all_args
                    if arg.annotation is not None
                    and not self._memo.name_matches(arg.annotation, *anytype_names)
                }
                if node.args.vararg:
                    if sys.version_info >= (3, 9):
                        container = Name("tuple", ctx=Load())
                    else:
                        container = self._get_import("typing", "Tuple")

                    annotation = Subscript(
                        container,
                        Tuple(
                            [node.args.vararg.annotation, Constant(Ellipsis)],
                            ctx=Load(),
                        ),
                    )
                    arg_annotations[node.args.vararg.arg] = annotation

                if node.args.kwarg:
                    if sys.version_info >= (3, 9):
                        container = Name("dict", ctx=Load())
                    else:
                        container = self._get_import("typing", "Dict")

                    annotation = Subscript(
                        container,
                        Tuple(
                            [Name("str", ctx=Load()), node.args.kwarg.annotation],
                            ctx=Load(),
                        ),
                    )
                    arg_annotations[node.args.kwarg.arg] = annotation

                if arg_annotations:
                    self._memo.variable_annotations.update(arg_annotations)

                has_annotated_return = bool(
                    self._memo.return_annotation
                ) and not self._memo.name_matches(
                    self._memo.return_annotation, *anytype_names
                )
            else:
                arg_annotations = None
                has_annotated_return = False

            self.generic_visit(node)

            if arg_annotations:
                func_name = self._get_import(
                    "typeguard._functions", "check_argument_types"
                )
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
            if (
                has_annotated_return
                and (not self._memo.is_async or not self._memo.has_yield_expressions)
                and not isinstance(node.body[-1], Return)
                and (
                    not isinstance(self._memo.return_annotation, Constant)
                    or self._memo.return_annotation.value is not None
                )
            ):
                func_name = self._get_import(
                    "typeguard._functions", "check_return_type"
                )
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
                if self._memo.parent and isinstance(self._memo.parent.node, ClassDef):
                    for decorator in node.decorator_list:
                        if (
                            isinstance(decorator, Name)
                            and decorator.id == "staticmethod"
                        ):
                            break
                        elif (
                            isinstance(decorator, Name)
                            and decorator.id == "classmethod"
                        ):
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
                names: list[str] = [node.name]
                memo = self._memo.parent
                while memo:
                    if isinstance(memo.node, (FunctionDef, AsyncFunctionDef)):
                        # This is a nested function. Use the function name as-is.
                        del names[:-1]
                        break
                    elif not isinstance(memo.node, ClassDef):
                        break

                    names.insert(0, memo.node.name)
                    memo = memo.parent

                func_reference: Name | Attribute = Name(id=names[0], ctx=Load())
                for name in names[1:]:
                    func_reference = Attribute(func_reference, name, ctx=Load())

                self._memo.call_memo_name.id = self._memo.get_unused_name("call_memo")
                call_memo_store_name = Name(
                    id=self._memo.call_memo_name.id, ctx=Store()
                )
                locals_call = Call(Name(id="locals", ctx=Load()), [], [])
                memo_expr = Call(
                    self._get_import("typeguard", "CallMemo"),
                    [func_reference, locals_call, *extra_args],
                    [],
                )
                node.body.insert(
                    0,
                    Assign([call_memo_store_name], memo_expr),
                )

                self._memo.insert_imports(node)

                # Rmove any placeholder "pass" at the end
                if isinstance(node.body[-1], Pass):
                    del node.body[-1]

        return node

    def visit_AsyncFunctionDef(
        self, node: AsyncFunctionDef
    ) -> FunctionDef | AsyncFunctionDef | None:
        return self.visit_FunctionDef(node)

    def visit_Return(self, node: Return) -> Return:
        """This injects type checks into "return" statements."""
        self.generic_visit(node)
        if (
            self._memo.should_instrument
            and self._memo.return_annotation
            and not self._memo.name_matches(
                self._memo.return_annotation, *anytype_names
            )
            and not self._memo.is_ignored_name(self._memo.return_annotation)
        ):
            func_name = self._get_import("typeguard._functions", "check_return_type")
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

    def visit_Yield(self, node: Yield) -> Yield | Call:
        """
        This injects type checks into "yield" expressions, checking both the yielded
        value and the value sent back to the generator, when appropriate.

        """
        self._memo.has_yield_expressions = True
        self.generic_visit(node)

        if (
            self._memo.should_instrument
            and self._memo.yield_annotation
            and not self._memo.name_matches(self._memo.yield_annotation, *anytype_names)
            and not self._memo.is_ignored_name(self._memo.yield_annotation)
        ):
            func_name = self._get_import("typeguard._functions", "check_yield_type")
            yieldval = node.value or Constant(None)
            node.value = Call(
                func_name,
                [yieldval, self._memo.get_call_memo_name()],
                [],
            )

        if (
            self._memo.should_instrument
            and self._memo.send_annotation
            and not self._memo.name_matches(self._memo.send_annotation, *anytype_names)
            and not self._memo.is_ignored_name(self._memo.send_annotation)
        ):
            func_name = self._get_import("typeguard._functions", "check_send_type")
            old_node = node
            call_node = Call(
                func_name,
                [old_node, self._memo.get_call_memo_name()],
                [],
            )
            copy_location(call_node, old_node)
            return call_node

        return node

    def visit_AnnAssign(self, node: AnnAssign) -> Any:
        """
        This injects a type check into a local variable annotation-assignment within a
        function body.

        """
        self.generic_visit(node)

        if isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef)):
            if self._memo.is_ignored_name(node.annotation):
                # Remove the node if there is no actual value assigned.
                # Otherwise, turn it into a regular assignment.
                if node.value:
                    return Assign((node.target,), node.value)
                else:
                    return None

            if isinstance(node.target, Name):
                self._memo.variable_annotations[node.target.id] = node.annotation
                if node.value:
                    # On Python < 3.10, if the annotation contains a binary "|", use the
                    # PEP 604 union transformer to turn such operations into
                    # typing.Unions
                    if UnionTransformer is not None and any(
                        isinstance(n, BinOp) for n in walk(node.annotation)
                    ):
                        union_name = self._get_import("typing", "Union")
                        node.annotation = UnionTransformer(union_name).visit(
                            node.annotation
                        )

                    func_name = self._get_import(
                        "typeguard._functions", "check_variable_assignment"
                    )
                    node.value = Call(
                        func_name,
                        [
                            node.value,
                            Constant(node.target.id),
                            node.annotation,
                            self._memo.get_call_memo_name(),
                        ],
                        [],
                    )

        return node

    def visit_Assign(self, node: Assign) -> Any:
        """
        This injects a type check into a local variable assignment within a function
        body. The variable must have been annotated earlier in the function body.

        """
        self.generic_visit(node)

        # Only instrument function-local assignments
        if isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef)):
            targets: list[dict[Constant, expr | None]] = []
            check_required = False
            for target in node.targets:
                elts: Sequence[expr]
                if isinstance(target, Name):
                    elts = [target]
                elif isinstance(target, Tuple):
                    elts = target.elts
                else:
                    continue

                annotations_: dict[Constant, expr | None] = {}
                for exp in elts:
                    prefix = ""
                    if isinstance(exp, Starred):
                        exp = exp.value
                        prefix = "*"

                    if isinstance(exp, Name):
                        name = prefix + exp.id
                        annotation = self._memo.variable_annotations.get(exp.id)
                        if annotation:
                            annotations_[Constant(name)] = annotation
                            check_required = True
                        else:
                            annotations_[Constant(name)] = None

                targets.append(annotations_)

            if check_required:
                # Replace missing annotations with typing.Any
                for item in targets:
                    for key, expression in item.items():
                        if expression is None:
                            item[key] = self._get_import("typing", "Any")

                if len(targets) == 1 and len(targets[0]) == 1:
                    func_name = self._get_import(
                        "typeguard._functions", "check_variable_assignment"
                    )
                    target_varname = next(iter(targets[0]))
                    node.value = Call(
                        func_name,
                        [
                            node.value,
                            target_varname,
                            targets[0][target_varname],
                            self._memo.get_call_memo_name(),
                        ],
                        [],
                    )
                elif targets:
                    func_name = self._get_import(
                        "typeguard._functions", "check_multi_variable_assignment"
                    )
                    targets_arg = List(
                        [
                            Dict(keys=list(target), values=list(target.values()))
                            for target in targets
                        ],
                        ctx=Load(),
                    )
                    node.value = Call(
                        func_name,
                        [node.value, targets_arg, self._memo.get_call_memo_name()],
                        [],
                    )

        return node

    def visit_NamedExpr(self, node: NamedExpr) -> Any:
        """This injects a type check into an assignment expression (a := foo())."""
        self.generic_visit(node)

        # Only instrument function-local assignments
        if isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef)) and isinstance(
            node.target, Name
        ):
            # Bail out if no matching annotation is found
            annotation = self._memo.variable_annotations.get(node.target.id)
            if annotation is None:
                return node

            func_name = self._get_import(
                "typeguard._functions", "check_variable_assignment"
            )
            node.value = Call(
                func_name,
                [
                    node.value,
                    Constant(node.target.id),
                    annotation,
                    self._memo.get_call_memo_name(),
                ],
                [],
            )

        return node

    def visit_AugAssign(self, node: AugAssign) -> Any:
        """
        This injects a type check into an augmented assignment expression (a += 1).

        """
        self.generic_visit(node)

        # Only instrument function-local assignments
        if isinstance(self._memo.node, (FunctionDef, AsyncFunctionDef)) and isinstance(
            node.target, Name
        ):
            # Bail out if no matching annotation is found
            annotation = self._memo.variable_annotations.get(node.target.id)
            if annotation is None:
                return node

            # Bail out if the operator is not found (newer Python version?)
            try:
                operator_func_name = aug_assign_functions[node.op.__class__]
            except KeyError:
                return node

            operator_func = self._get_import("operator", operator_func_name)
            operator_call = Call(
                operator_func, [Name(node.target.id, ctx=Load()), node.value], []
            )
            check_call = Call(
                self._get_import("typeguard._functions", "check_variable_assignment"),
                [
                    operator_call,
                    Constant(node.target.id),
                    annotation,
                    self._memo.get_call_memo_name(),
                ],
                [],
            )
            return Assign(targets=[node.target], value=check_call)

        return node

    def visit_If(self, node: If) -> Any:
        """
        This blocks names from being collected from a module-level
        "if typing.TYPE_CHECKING:" block, so that they won't be type checked.

        """
        self.generic_visit(node)
        if (
            self._memo is self._module_memo
            and isinstance(node.test, Name)
            and self._memo.name_matches(node.test, "typing.TYPE_CHECKING")
        ):
            collector = NameCollector()
            collector.visit(node)
            self._memo.ignored_names.update(collector.names)

        return node
