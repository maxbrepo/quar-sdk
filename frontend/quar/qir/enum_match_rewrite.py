"""Guarded match-arm binding substitution for the experimental flattened ABI.

Only expression references are rewritten; binding assignments and shadowing fail
closed. The caller must place the rewritten arm behind a matching tag guard.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace

from ..ast_nodes import Assignment, MatchStatement, Variable, VariableDeclaration
from ..ir.model import IRAssign, IRDeclare, IRMatch, IRReference
from .enum_binding_plan import QEnumArmPlan
from .enum_layout import QIREnumLayoutError
from .model import QType


def rewrite_match_arm(body: object, plan: QEnumArmPlan, available: dict[str, QType], *, legacy: bool) -> object:
    """Replace scoped binding reads with typed payload slots, without mutation."""
    bindings = {binding.name: binding for binding in plan.bindings}
    for binding in plan.bindings:
        if binding.name in available:
            raise QIREnumLayoutError("Match binding shadows an existing variable")
        if available.get(binding.slot) != binding.type:
            raise QIREnumLayoutError("Missing or incorrectly typed payload slot parameter")

    reference = IRReference if legacy else Variable
    assignment = IRAssign if legacy else Assignment
    declaration = IRDeclare if legacy else VariableDeclaration
    nested_match = IRMatch if legacy else MatchStatement

    def visit(node: object) -> object:
        if isinstance(node, nested_match):
            # A nested match introduces a new lexical binding scope. Until
            # scope-aware rewriting exists, reject it instead of capturing
            # or substituting the wrong payload slot.
            raise QIREnumLayoutError("Nested match in a bound arm is not supported yet")
        if isinstance(node, reference) and node.name in bindings:
            return reference(bindings[node.name].slot)
        if isinstance(node, (assignment, declaration)) and node.name in bindings:
            raise QIREnumLayoutError("Match binding cannot be assigned or redeclared")
        if isinstance(node, (list, tuple)):
            return type(node)(visit(item) for item in node)
        if is_dataclass(node) and not isinstance(node, type):
            return replace(node, **{field.name: visit(getattr(node, field.name)) for field in fields(node)})
        return node

    return visit(body)
