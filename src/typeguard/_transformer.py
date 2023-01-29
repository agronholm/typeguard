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
    keyword,
)


class TypeguardTransformer(NodeTransformer):
    def __init__(self) -> None:
        self._parents: list[ClassDef | FunctionDef | AsyncFunctionDef] = []
        self._contains_yields: set[FunctionDef] = set()
        self._used_names = set()
        self._used_imports = set()
        self._store_names = {
            "call_memo": Name(id="_call_memo", ctx=Store()),
            "check_argument_types": Name(
                id="_typeguard_check_argument_types", ctx=Store()
            ),
            "check_return_type": Name(id="_typeguard_check_return_type", ctx=Store()),
            "check_yield_type": Name(id="_typeguard_check_yieldtype", ctx=Store()),
            "check_send_type": Name(id="_typeguard_check_send_type", ctx=Store()),
        }
        self._load_names = {
            key: Name(id=value.id, ctx=Load())
            for key, value in self._store_names.items()
        }

    def visit_Module(self, node: Module):
        self.generic_visit(node)

        # Ensure that there are no name conflicts
        for key, name in self._load_names.items():
            while name.id in self._used_names:
                name.id += "_"
                self._store_names[key].id = name.id

        # Insert "import typeguard" after any "from __future__ ..." imports
        for i, child in enumerate(node.body):
            if isinstance(child, ImportFrom) and child.module == "__future__":
                continue
            elif isinstance(child, Expr) and isinstance(child.value, Str):
                continue  # module docstring
            else:
                aliases = [alias(funcname) for funcname in sorted(self._used_imports)]
                node.body.insert(i, ImportFrom("typeguard", aliases))
                break

        return node

    def visit_ClassDef(self, node: ClassDef):
        self._used_names.add(node.name)
        self._parents.append(node)
        self.generic_visit(node)
        self._parents.pop()
        return node

    def visit_Return(self, node: Return):
        if self._parents[-1].returns:
            retval = node.value or Constant(None)
            node = Return(
                Call(
                    Name(id="check_return_type", ctx=Load()),
                    [retval, self._load_names["call_memo"]],
                    [],
                )
            )
            self._used_imports.add("check_return_type")

        self.generic_visit(node)
        return node

    def visit_Yield(self, node: Yield):
        self._contains_yields.add(self._parents[-1])
        if self._parents[-1].returns:
            yieldval = node.value or Name(id="None", ctx=Load())
            yield_node = Yield(
                Call(
                    Name(id="check_yield_type", ctx=Load()),
                    [yieldval, self._load_names["call_memo"]],
                    [],
                )
            )
            self._used_imports.add("check_yield_type")

            node = Call(
                Name(id="check_send_type", ctx=Load()),
                [yield_node, self._load_names["call_memo"]],
                [],
            )
            self._used_imports.add("check_send_type")
        else:
            self.generic_visit(node)

        return node

    def visit_Assign(self, node: Assign) -> Assign:
        for target in node.targets:
            if isinstance(target, Name):
                self._used_names.add(target.id)

        return node

    def visit_FunctionDef(
        self,
        node: FunctionDef | AsyncFunctionDef,
        *,
        has_self_arg: bool = False,
    ):
        self._used_names.add(node.name)
        has_annotated_args = any(arg for arg in node.args.args if arg.annotation)
        has_annotated_return = bool(node.returns)
        if has_annotated_args or has_annotated_return:
            func_reference = Name(id=node.name, ctx=Load())
            if self._parents and isinstance(self._parents[-1], ClassDef):
                # This is a method, not a free function.
                # Walk through the parents and build the attribute chain from containing
                # classes like A.B.C.methodname
                previous_attribute: Attribute | None = None
                for parent_node in reversed(self._parents):
                    if isinstance(parent_node, ClassDef):
                        attrname = (
                            previous_attribute.value.id
                            if previous_attribute
                            else func_reference.id
                        )
                        attribute = Attribute(
                            Name(id=parent_node.name, ctx=Load()),
                            attrname,
                            ctx=Load(),
                        )
                        if previous_attribute is None:
                            func_reference = attribute
                        else:
                            previous_attribute.value = attribute

                        previous_attribute = attribute
                    else:
                        break

                for expr in node.decorator_list:
                    if isinstance(expr, Name) and expr.id == "staticmethod":
                        break
                else:
                    has_self_arg = True

            locals_call = Call(Name(id="locals", ctx=Load()), [], [])
            memo_expr = Call(
                Name(id="CallMemo", ctx=Load()),
                [func_reference, locals_call],
                [
                    keyword("has_self_arg", Constant(has_self_arg, ctx=Load())),
                    keyword(
                        "unwrap_generator_annotations",
                        Constant(True, ctx=Load()),
                    ),
                ],
            )
            node.body.insert(
                0,
                Assign([self._store_names["call_memo"]], memo_expr),
            )
            self._used_imports.add("CallMemo")

        if has_annotated_args:
            node.body.insert(
                1,
                Expr(
                    Call(
                        Name(id="check_argument_types", ctx=Load()),
                        [self._load_names["call_memo"]],
                        [],
                    )
                ),
            )
            self._used_imports.add("check_argument_types")

        self._parents.append(node)
        self.generic_visit(node)
        self._parents.pop()

        # Add a checked "return None" to the end if there's no explicit return
        if node not in self._contains_yields:
            if has_annotated_return and not isinstance(node.body[-1], Return):
                # Replace a placeholder "pass" at the end
                if isinstance(node.body[-1], Pass):
                    del node.body[-1]

                node.body.append(
                    Return(
                        Call(
                            Name(id="check_return_type", ctx=Load()),
                            [
                                Constant(None),
                                self._load_names["call_memo"],
                            ],
                            [],
                        )
                    ),
                )
                self._used_imports.add("check_return_type")
        else:
            self._contains_yields.remove(node)

        return node

    def visit_AsyncFunctionDef(self, node: AsyncFunctionDef):
        self.visit_FunctionDef(node)
        return node
