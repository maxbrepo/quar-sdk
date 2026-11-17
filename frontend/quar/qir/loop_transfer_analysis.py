"""Language-neutral analysis of loop-local break/continue transfers.

Nested loops own their transfers. This module never rewrites control flow;
callers must still reject transfers their lowering cannot represent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..ast_nodes import (BreakStatement, ContinueStatement, IfStatement,
                         WhileStatement, ForStatement, LoopStatement, DoWhileStatement)
from ..ir.model import IRBreak, IRContinue, IRIf, IRWhile, IRFor, IRLoop, IRDoWhile


@dataclass(frozen=True)
class LoopTransferPlan:
    breaks: int = 0
    continues: int = 0
    conditional: bool = False
    nonterminal: bool = False

    @property
    def needs_general_cfg(self) -> bool:
        """True when a simple terminal-transfer lowering is insufficient."""
        return self.conditional or self.nonterminal


def analyze_loop_transfers(body: Iterable[object]) -> LoopTransferPlan:
    """Count transfers owned by this loop, excluding nested-loop transfers."""
    breaks = continues = 0
    conditional = nonterminal = False
    nested_types = (WhileStatement, ForStatement, LoopStatement, DoWhileStatement,
                    IRWhile, IRFor, IRLoop, IRDoWhile)

    def visit(statements: tuple[object, ...], in_condition: bool) -> None:
        nonlocal breaks, continues, conditional, nonterminal
        for index, statement in enumerate(statements):
            if isinstance(statement, nested_types):
                continue
            if isinstance(statement, (BreakStatement, IRBreak, ContinueStatement, IRContinue)):
                breaks += isinstance(statement, (BreakStatement, IRBreak))
                continues += isinstance(statement, (ContinueStatement, IRContinue))
                conditional |= in_condition
                nonterminal |= index != len(statements) - 1
            elif isinstance(statement, (IfStatement, IRIf)):
                visit(tuple(statement.then_body), True)
                visit(tuple(statement.else_body), True)

    visit(tuple(body), False)
    return LoopTransferPlan(breaks, continues, conditional, nonterminal)
