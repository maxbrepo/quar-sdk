"""Verify the shared loop transfer analysis on AST and executable IR."""
import unittest

from frontend.quar.ast_nodes import (BreakStatement, ContinueStatement,
                                     IfStatement, Integer, WhileStatement)
from frontend.quar.ir.model import IRBreak, IRContinue, IRIf, IRLiteral, IRWhile
from frontend.quar.qir.loop_transfer_analysis import analyze_loop_transfers


class LoopTransferAnalysisTests(unittest.TestCase):
    def test_terminal_break_is_simple_in_both_representations(self):
        self.assertEqual(analyze_loop_transfers([BreakStatement()]),
                         analyze_loop_transfers((IRBreak(),)))
        self.assertFalse(analyze_loop_transfers([BreakStatement()]).needs_general_cfg)

    def test_conditional_continue_requires_general_cfg(self):
        ast = [IfStatement(Integer(1), [ContinueStatement()], [])]
        ir = (IRIf(IRLiteral(1), (IRContinue(),), ()),)
        self.assertEqual(analyze_loop_transfers(ast), analyze_loop_transfers(ir))
        self.assertTrue(analyze_loop_transfers(ast).needs_general_cfg)

    def test_nested_loop_transfers_are_not_attributed_to_outer_loop(self):
        ast = [WhileStatement(Integer(1), [BreakStatement()]), ContinueStatement()]
        ir = (IRWhile(IRLiteral(1), (IRBreak(),)), IRContinue())
        self.assertEqual(analyze_loop_transfers(ast), analyze_loop_transfers(ir))
        self.assertEqual(analyze_loop_transfers(ast).breaks, 0)
        self.assertEqual(analyze_loop_transfers(ast).continues, 1)

    def test_nested_conditions_are_classified_in_both_representations(self):
        ast = [IfStatement(Integer(1), [IfStatement(Integer(1), [BreakStatement()], [])], [])]
        ir = (IRIf(IRLiteral(1), (IRIf(IRLiteral(1), (IRBreak(),), ()),), ()),)
        self.assertEqual(analyze_loop_transfers(ast), analyze_loop_transfers(ir))
        self.assertEqual(analyze_loop_transfers(ast).breaks, 1)
        self.assertTrue(analyze_loop_transfers(ast).conditional)

    def test_transfer_in_inner_loop_condition_does_not_escape(self):
        ast = [WhileStatement(Integer(1), [IfStatement(Integer(1), [BreakStatement()], [])])]
        ir = (IRWhile(IRLiteral(1), (IRIf(IRLiteral(1), (IRBreak(),), ()),)),)
        self.assertEqual(analyze_loop_transfers(ast), analyze_loop_transfers(ir))
        self.assertEqual(analyze_loop_transfers(ast).breaks, 0)

    def test_nonterminal_transfer_is_identified(self):
        plan = analyze_loop_transfers([BreakStatement(), ContinueStatement()])
        self.assertEqual((plan.breaks, plan.continues), (1, 1))
        self.assertTrue(plan.nonterminal)


if __name__ == '__main__':
    unittest.main()
