"""QIR-04: direct function calls, frame isolation and fail-closed guards."""
from __future__ import annotations

import unittest

from frontend.quar.ast_nodes import (Assignment, FunctionCall, FunctionDefinition,
                                     FunctionParameter, Integer, ReturnStatement,
                                     Variable, VariableDeclaration)
from frontend.quar.qir.model import (QBlock, QFunction, QInstruction, QModule,
                                     QReturn, QType, QValue)
from frontend.quar.qir.program_lowering import QIRProgramLoweringError, lower_ast_program
from frontend.quar.qir.validation import QIRValidationError, validate_module
from qrvm.qir_program_backend import QIRProgramBackendError, compile_qir_program
from tools.qir_cycle5_03_parity import execute
from tools.qir_cycle5_04_functions import ROOT, SAMPLES, build_report


class QIR04FunctionTests(unittest.TestCase):
    def test_nine_catalog_programs_execute_through_qir(self):
        report = build_report(ROOT)
        self.assertEqual(report["verified_programs"], 9)
        self.assertEqual(len(report["verified_entries"]), len(SAMPLES))
        self.assertEqual(report["chapter_progress"][0]["verified"], 9)
        self.assertEqual(report["chapter_progress"][0]["total"], 36)
        self.assertEqual(report["chapter_progress"][0]["percent"], 25.0)
        self.assertEqual(report["qir_percent"], 3.57)
        self.assertEqual(report["total_programs"], 252)

    def test_direct_call_is_in_qir_and_qrvm_not_ast_fallback(self):
        source = [FunctionDefinition("i32", "identity", [FunctionParameter("i32", "x")],
                                     [ReturnStatement(Variable("x"))]),
                  VariableDeclaration("i32", "result", FunctionCall("identity", [Integer(42)])),
                  FunctionCall("print", [Variable("result")])]
        qir = lower_ast_program(source)
        entry_ops = qir.functions[0].blocks[0].instructions
        self.assertIn("call", [instruction.opcode for instruction in entry_ops])
        package = compile_qir_program(qir)
        self.assertEqual(set(package["functions"]), {"identity"})
        self.assertEqual(execute(package), "42\n")

    def test_forward_call_and_nested_calls(self):
        source = [FunctionDefinition("i32", "first", [FunctionParameter("i32", "x")],
                    [ReturnStatement(FunctionCall("second", [Variable("x")]))]),
                  FunctionDefinition("i32", "second", [FunctionParameter("i32", "y")],
                    [ReturnStatement(Variable("y"))]),
                  FunctionCall("print", [FunctionCall("first", [Integer(19)])])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(source))), "19\n")

    def test_separate_function_local_frames(self):
        source = [FunctionDefinition("i32", "identity", [FunctionParameter("i32", "x")],
                    [Assignment("x", Integer(8)), ReturnStatement(Variable("x"))]),
                  FunctionCall("print", [FunctionCall("identity", [Integer(1)])]),
                  FunctionCall("print", [FunctionCall("identity", [Integer(2)])])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(source))), "8\n8\n")

    def test_first_assignment_requires_opt_in(self):
        source = [Assignment("x", Integer(7)), FunctionCall("print", [Variable("x")])]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(source)
        self.assertEqual(execute(compile_qir_program(lower_ast_program(
            source, allow_inferred_declarations=True))), "7\n")

    def test_void_function_is_supported(self):
        source = [FunctionDefinition("void", "f", [], [ReturnStatement(None)]),
                  FunctionCall("f", [])]
        self.assertEqual(execute(compile_qir_program(lower_ast_program(source))), "")

    def test_unsupported_default_parameter_is_rejected(self):
        source = [FunctionDefinition("i32", "f", [FunctionParameter("i32", "x", Integer(2))],
                                     [ReturnStatement(Variable("x"))]),
                  FunctionCall("print", [Integer(2)])]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(source)

    def test_unknown_and_wrong_arity_calls_fail_closed(self):
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program([FunctionCall("print", [FunctionCall("missing", [])])])
        source = [FunctionDefinition("i32", "f", [FunctionParameter("i32", "x")],
                                     [ReturnStatement(Variable("x"))]),
                  FunctionCall("print", [FunctionCall("f", [])])]
        with self.assertRaises(QIRProgramLoweringError):
            lower_ast_program(source)

    def test_qir_validator_rejects_wrong_call_signature(self):
        i32 = QType("i32")
        function = QFunction("f", i32, (QValue("x", i32),),
                             (QBlock("entry", (), QReturn(QValue("x", i32))),))
        entry = QFunction("__qir_entry", QType("void"), (),
                          (QBlock("entry", (QInstruction("call", (), QValue("r", i32), "f"),), QReturn()),))
        with self.assertRaises(QIRValidationError):
            validate_module(QModule("invalid", (entry, function)))

    def test_backend_rejects_module_without_entry(self):
        function = QFunction("f", QType("i32"), (),
                             (QBlock("entry", (QInstruction("const", (), QValue("r", QType("i32")), 1),),
                                     QReturn(QValue("r", QType("i32")))),))
        with self.assertRaises(QIRProgramBackendError):
            compile_qir_program(QModule("no_entry", (function,)))


if __name__ == "__main__":
    unittest.main()
