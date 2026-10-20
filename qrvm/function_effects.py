"""Explicit, conservative function-effect summaries for optional flow analysis.

Only audited/declared summaries are trusted. Unlisted calls have unknown effects.
This module does not infer purity or change runtime behavior.
"""
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class FunctionEffects:
    """Names of optional variables that a call may modify.

    An empty set means the function does not modify tracked optional state.
    The caller must supply a sound summary; this is not an inference result.
    """
    modifies: frozenset[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, 'modifies', frozenset(self.modifies))
        if not all(isinstance(name, str) and name for name in self.modifies):
            raise ValueError('Effect targets must be non-empty variable names')


def call_invalidations(expression, optional_names, summaries: Mapping[str, FunctionEffects], alias_state=None):
    """Return optional names whose presence guarantees a call may invalidate."""
    from frontend.quar.ast_nodes import BinaryOperation, FunctionCall, UnaryOperation

    optional_names = frozenset(optional_names)
    if expression is None:
        return frozenset()
    if isinstance(expression, FunctionCall):
        invalidated = frozenset()
        for arg in expression.arguments:
            invalidated |= call_invalidations(arg, optional_names, summaries, alias_state)
        if expression.name == 'present' and len(expression.arguments) == 1:
            return invalidated
        summary = summaries.get(expression.name)
        if summary is None:
            return invalidated | optional_names
        return invalidated | ((alias_state.affected(summary.modifies & optional_names) if alias_state is not None else summary.modifies & optional_names))
    if isinstance(expression, BinaryOperation):
        return (call_invalidations(expression.left, optional_names, summaries, alias_state)
                | call_invalidations(expression.right, optional_names, summaries, alias_state))
    if isinstance(expression, UnaryOperation):
        return call_invalidations(expression.operand, optional_names, summaries, alias_state)
    return frozenset()


def infer_function_effects(functions, tracked_names):
    """Infer conservative summaries for simple, closed AST function bodies.

    Unknown callees, unsupported statements and indirect state changes remain
    unknown (their functions are omitted from the returned mapping). No purity
    claims are made for external functions or object/array mutations.
    """
    from frontend.quar.ast_nodes import (
        Assignment, VariableDeclaration, ConstantDeclaration, FunctionDefinition,
        FunctionCall, BinaryOperation, UnaryOperation, ReturnStatement,
        IfStatement, WhileStatement, ForStatement, LoopStatement, DoWhileStatement,
        BreakStatement, ContinueStatement, Boolean, Integer, Double, String,
        Char, Variable,
    )

    tracked = frozenset(tracked_names)
    definitions = {}
    for fn in functions:
        if not isinstance(fn, FunctionDefinition) or fn.name in definitions:
            raise ValueError('Expected uniquely named FunctionDefinition entries')
        definitions[fn.name] = fn

    def expression_effects(expr, summaries):
        if expr is None or isinstance(expr, (Boolean, Integer, Double, String, Char, Variable)):
            return frozenset()
        if isinstance(expr, UnaryOperation):
            return expression_effects(expr.operand, summaries)
        if isinstance(expr, BinaryOperation):
            left = expression_effects(expr.left, summaries)
            right = expression_effects(expr.right, summaries)
            return None if left is None or right is None else left | right
        if isinstance(expr, FunctionCall):
            accumulated = frozenset()
            for arg in expr.arguments:
                effect = expression_effects(arg, summaries)
                if effect is None:
                    return None
                accumulated |= effect
            if expr.name == 'present' and len(expr.arguments) == 1:
                return accumulated
            called = summaries.get(expr.name)
            return None if called is None else accumulated | called
        return None

    def statements_effects(body, summaries, locals_):
        modified = frozenset()
        for statement in body:
            if isinstance(statement, (VariableDeclaration, ConstantDeclaration)):
                effects = expression_effects(statement.value, summaries)
                locals_.add(statement.name)
            elif isinstance(statement, Assignment):
                effects = expression_effects(statement.value, summaries)
                if statement.name in tracked and statement.name not in locals_:
                    modified |= frozenset({statement.name})
            elif isinstance(statement, ReturnStatement):
                effects = expression_effects(statement.value, summaries)
            elif isinstance(statement, IfStatement):
                effects = expression_effects(statement.condition, summaries)
                a = statements_effects(statement.then_body, summaries, set(locals_))
                b = statements_effects(statement.else_body, summaries, set(locals_))
                if a is None or b is None:
                    return None
                effects = None if effects is None else effects | a | b
            elif isinstance(statement, (WhileStatement, DoWhileStatement)):
                effects = expression_effects(statement.condition, summaries)
                nested = statements_effects(statement.body, summaries, set(locals_))
                effects = None if effects is None or nested is None else effects | nested
            elif isinstance(statement, LoopStatement):
                effects = statements_effects(statement.body, summaries, set(locals_))
            elif isinstance(statement, ForStatement):
                # Counter is local to the loop; the bounds and comparison may call functions.
                scoped = set(locals_) | {statement.counter_name}
                effects = expression_effects(statement.start, summaries)
                cmp_effects = expression_effects(statement.comparison, summaries)
                nested = statements_effects(statement.body, summaries, scoped)
                effects = None if effects is None or cmp_effects is None or nested is None else effects | cmp_effects | nested
            elif isinstance(statement, (BreakStatement, ContinueStatement)):
                effects = frozenset()
            elif isinstance(statement, FunctionCall):
                effects = expression_effects(statement, summaries)
            else:
                return None
            if effects is None:
                return None
            modified |= effects
        return modified

    # Start with an optimistic bottom element only for internal calls. Iterate
    # until summaries stabilize; unresolved/external calls remain unknown.
    summaries = {name: frozenset() for name in definitions}
    while True:
        updated = {}
        for name, fn in definitions.items():
            params = {parameter.name for parameter in fn.parameters}
            result = statements_effects(fn.body, summaries, params)
            if result is not None:
                updated[name] = result
        if updated == summaries:
            break
        summaries = updated
    return {name: FunctionEffects(effects) for name, effects in summaries.items()}
