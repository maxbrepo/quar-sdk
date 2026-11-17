"""QIR-05 regression coverage for branches, scope, phi and catalog parity."""
from __future__ import annotations

import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionCall,
                                     IfStatement, Integer, Variable,
                                     VariableDeclaration)
from frontend.quar.qir.model import (QBlock, QBranch, QFunction, QJump, QModule,
                                     QPhi, QReturn, QType, QValue)
from frontend.quar.qir.program_lowering import QIRProgramLoweringError, lower_ast_program
from frontend.quar.qir.validation import QIRValidationError, validate_module
from qrvm.qir_program_backend import QIRProgramBackendError, compile_qir_program
from tools.qir_cycle5_03_parity import execute
from tools.qir_cycle5_05_branches import BASELINE, ROOT, SAMPLES, build_report


class QIR05BranchTests(unittest.TestCase):
    def test_twenty_one_complete_programs(self):
        report = build_report(ROOT)
        self.assertEqual(report["verified_programs"], 21)
        self.assertEqual(len(report["verified_entries"]), len(SAMPLES))
        self.assertEqual(report["chapter_progress"][0]["verified"], 21)
        self.assertEqual(report["chapter_progress"][0]["total"], 36)
        self.assertEqual(report["chapter_progress"][0]["percent"], 58.33)
        self.assertEqual(report["total_programs"], 252)
        self.assertEqual(report["qir_percent"], 8.33)

    def test_inventory_is_a_test_fixture_not_documentation(self):
        self.assertTrue((ROOT / BASELINE).is_file())
        self.assertTrue(BASELINE.startswith("tests/data/qir/"))

    def test_branch_false_and_true_paths(self):
        for initial, expected in ((0, "3\n"), (1, "2\n")):
            with self.subTest(initial=initial):
                ast = [VariableDeclaration("i32", "x", Integer(initial)),
                       IfStatement(BinaryOperation(Variable("x"), "==", Integer(1)),
                                   [Assignment("x", Integer(2))],
                                   [Assignment("x", Integer(3))]),
                       FunctionCall("print", [Variable("x")])]
                qir = lower_ast_program(ast)
                self.assertTrue(any(block.phis for block in qir.functions[0].blocks))
                self.assertEqual(execute(compile_qir_program(qir)), expected)

    def test_branch_without_else_preserves_original_value(self):
        ast = [VariableDeclaration("i32", "x", Integer(10)),
               IfStatement(BinaryOperation(Variable("x"), "==", Integer(11)),
                           [Assignment("x", Integer(20))], []),
               FunctionCall("print", [Variable("x")])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(ast))), "10\n")

    def test_nested_branches_preserve_outer_assignment(self):
        ast = [VariableDeclaration("i32", "x", Integer(0)),
               IfStatement(BinaryOperation(Variable("x"), "==", Integer(0)),
                           [IfStatement(BinaryOperation(Variable("x"), "==", Integer(0)),
                                        [Assignment("x", Integer(7))], [])], []),
               FunctionCall("print", [Variable("x")])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(ast))), "7\n")

    def test_branch_local_does_not_escape(self):
        ast = [IfStatement(BinaryOperation(Integer(1), "==", Integer(1)),
                           [VariableDeclaration("i32", "inside", Integer(4))], []),
               FunctionCall("print", [Variable("inside")])]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(ast)

    def test_branch_cannot_mutate_constant(self):
        from frontend.quar.ast_nodes import ConstantDeclaration
        ast = [ConstantDeclaration("i32", "x", Integer(1)),
               IfStatement(BinaryOperation(Integer(1), "==", Integer(1)),
                           [Assignment("x", Integer(2))], [])]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(ast)

    def test_invalid_phi_incoming_is_rejected(self):
        i32 = QType("i32")
        condition = QValue("flag", QType("bool"))
        v = QValue("x", i32)
        result = QValue("merged", i32)
        module = QModule("bad", (QFunction("__qir_entry", QType("void"), (), (
            QBlock("entry", (), QBranch(condition, "yes", "no")),
            QBlock("yes", (), QJump("join")),
            QBlock("no", (), QJump("join")),
            QBlock("join", (), QReturn(), (QPhi(result, (("yes", v),)),)),
        )),))
        with self.assertRaises(QIRValidationError):
            validate_module(module)

    def test_cycles_fail_closed_without_loop_lowering(self):
        module = QModule("loop", (QFunction("__qir_entry", QType("void"), (), (
            QBlock("entry", (), QJump("repeat")),
            QBlock("repeat", (), QJump("repeat")),
        )),))
        with self.assertRaises(QIRProgramBackendError):
            compile_qir_program(module)


if __name__ == "__main__":
    unittest.main()
