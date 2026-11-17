"""Cycle 5 QIR-03: whole-program QIR execution and regression guards."""
from __future__ import annotations

from pathlib import Path
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionCall,
                                     Integer, Variable, VariableDeclaration)
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QModule, QReturn, QType, QValue
from frontend.quar.qir.program_lowering import QIRProgramLoweringError, lower_ast_program
from frontend.quar.qir.validation import QIRValidationError, validate_module
from main import build_frontend
from qrvm.qir_program_backend import QIRProgramBackendError, compile_qir_program
from tools.qir_cycle5_03_parity import ROOT, SAMPLES, build_report, execute
from qrvm.compiler import QRVMCompiler


class QIR03ProgramTests(unittest.TestCase):
    def test_three_real_chapter_one_programs_execute_through_qir(self):
        for relative in SAMPLES:
            with self.subTest(relative=relative):
                ast, _ = build_frontend((ROOT / relative).read_text(encoding="utf-8"))
                qir = lower_ast_program(ast)
                self.assertEqual(len(qir.functions), 1)
                self.assertEqual(qir.functions[0].return_type.name, "void")
                self.assertEqual(execute(compile_qir_program(qir)), execute(QRVMCompiler().compile(ast)))
                self.assertEqual(execute(compile_qir_program(qir)), "5\n")

    def test_progress_counts_only_complete_programs(self):
        report = build_report(ROOT)
        self.assertEqual(report["total_programs"], 252)
        self.assertEqual(report["verified_programs"], 3)
        self.assertEqual(report["chapter_progress"][0]["total"], 36)
        self.assertEqual(report["chapter_progress"][0]["verified"], 3)
        self.assertEqual(report["chapter_progress"][0]["percent"], 8.33)
        self.assertEqual(report["qir_percent"], 1.19)

    def test_unsupported_function_calls_are_rejected_without_ast_fallback(self):
        program = [FunctionCall("unknown", [])]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(program)

    def test_undeclared_or_constant_assignment_rejected(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([Assignment("x", Integer(2))])
        from frontend.quar.ast_nodes import ConstantDeclaration
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([ConstantDeclaration("i32", "x", Integer(1)),
                               Assignment("x", Integer(2))])

    def test_i32_literal_out_of_range_rejected(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([VariableDeclaration("i32", "x", Integer(2**31))])

    def test_qir_print_rejects_result_value(self):
        value = QValue("x", QType("bool"))
        malformed = QModule("bad", (QFunction("__qir_entry", QType("void"), (),
            (QBlock("entry", (QInstruction("const", (), value, True),
                              QInstruction("print", (value,), QValue("invalid_result", QType("bool")))), QReturn()),)),))
        with self.assertRaises(QIRValidationError):
            validate_module(malformed)

    def test_backend_supports_acyclic_jump_without_ast_fallback(self):
        from frontend.quar.qir.model import QJump
        module = QModule("control", (QFunction("__qir_entry", QType("void"), (),
            (QBlock("entry", (), QJump("end")), QBlock("end", (), QReturn()))),))
        self.assertEqual(execute(compile_qir_program(module)), "")

    def test_program_result_is_not_compiled_from_ast(self):
        ast = [VariableDeclaration("i32", "x", Integer(2)),
               Assignment("x", BinaryOperation(Variable("x"), "+", Integer(3))),
               FunctionCall("print", [Variable("x")])]
        qir = lower_ast_program(ast)
        self.assertEqual([op.opcode for op in qir.functions[0].blocks[0].instructions],
                         ["const", "const", "add", "print"])
        self.assertEqual(execute(compile_qir_program(qir)), "5\n")


if __name__ == "__main__":
    unittest.main()
