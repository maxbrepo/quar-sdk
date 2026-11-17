"""Cycle 5 checkpoint 02: deterministic catalog and opt-in QIR function adapter."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from frontend.quar.ast_nodes import (BinaryOperation, FunctionDefinition, FunctionParameter,
                                     Integer, ReturnStatement, Variable)
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.model import QBlock, QFunction, QJump, QReturn, QType, QValue
from qrvm.bytecode_format import wrap_legacy_program
from qrvm.bytecode_verifier import verify_bytecode
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode
from qrvm.qir_backend import QIRQRVMBackendError, compile_qir_function
from qrvm.vm import QRVM
from tools.qir_cycle5_inventory import build_inventory

ROOT = Path(__file__).resolve().parents[1]


def execute_function(function, arg):
    """Run an isolated function through the existing QRVM and return stdout."""
    package = {"instructions": [(OpCode.PUSH_INT, arg), (OpCode.CALL, ("compute", 1)),
                                (OpCode.PRINT, None), (OpCode.HALT, None)],
               "functions": {"compute": function}}
    verify_bytecode(wrap_legacy_program(package))
    output = io.StringIO()
    vm = QRVM()
    with contextlib.redirect_stdout(output):
        vm.run(package)
    if vm.stack:
        raise AssertionError("QRVM operand stack was not cleared")
    return output.getvalue()


class QIR02InventoryTests(unittest.TestCase):
    def test_inventory_is_deterministic(self):
        a, b = build_inventory(ROOT), build_inventory(ROOT)
        self.assertEqual(a, b)
        self.assertEqual(len(a["catalog_sha256"]), 64)
        self.assertEqual(a["total_source_files"], len(list((ROOT / "examples").rglob("*.vq"))))

    def test_chapter_profiles_and_unique_paths(self):
        report = build_inventory(ROOT)
        self.assertEqual(len(report["chapter_progress"]), 18)
        self.assertEqual(report["total_programs"], sum(c["total"] for c in report["chapter_progress"]))
        self.assertEqual(len({p["path"] for p in report["programs"]}), report["total_programs"])
        self.assertTrue(all(1 <= p["chapter"] <= 18 for p in report["programs"]))
        self.assertTrue(all(p["qir_status"] == "pending" for p in report["programs"]))
        self.assertEqual(report["verified_programs"], 0)

    def test_imported_modules_are_not_standalone_programs(self):
        report = build_inventory(ROOT)
        self.assertTrue(any(e["reason"] == "chapter 13 imported module" for e in report["excluded_sources"]))
        self.assertTrue(all(not p["path"].endswith("/math.vq") for p in report["programs"]
                            if p["chapter"] == 13))

    def test_candidate_negative_is_not_assumed_to_pass(self):
        report = build_inventory(ROOT)
        self.assertTrue(any(p["candidate_negative"] for p in report["programs"]))
        self.assertTrue(all(p["qir_status"] == "pending" for p in report["programs"]
                            if p["candidate_negative"]))


class QIR02FunctionAdapterTests(unittest.TestCase):
    def function(self, expression):
        return FunctionDefinition("int", "compute", [FunctionParameter("int", "x")],
                                  [ReturnStatement(expression)])

    def test_qir_execution_matches_ast_compiler_for_small_arithmetic(self):
        for expression, arguments in (
            (BinaryOperation(Variable("x"), "+", Integer(3)), (-4, 0, 9)),
            (BinaryOperation(Variable("x"), "-", Integer(2)), (0, 10)),
            (BinaryOperation(Variable("x"), "*", Integer(4)), (-2, 7)),
            (Variable("x"), (0, 42)),
        ):
            with self.subTest(expression=expression):
                ast = self.function(expression)
                qir = lower_ast_function(ast)
                adapted = compile_qir_function(qir)
                baseline = QRVMCompiler().compile_function(ast)
                for argument in arguments:
                    self.assertEqual(execute_function(adapted, argument),
                                     execute_function(baseline, argument))

    def test_reject_control_flow(self):
        v = QValue("x", QType("i32"))
        qir = QFunction("compute", QType("i32"), (v,),
                        (QBlock("entry", (), QJump("exit")),
                         QBlock("exit", (), QReturn(v))))
        with self.assertRaises(QIRQRVMBackendError):
            compile_qir_function(qir)

    def test_reject_narrow_integer_types(self):
        v = QValue("x", QType("i8"))
        qir = QFunction("compute", QType("i8"), (v,),
                        (QBlock("entry", (), QReturn(v)),))
        with self.assertRaises(QIRQRVMBackendError):
            compile_qir_function(qir)

    def test_reject_unimplemented_operation(self):
        ast = self.function(BinaryOperation(Variable("x"), "/", Integer(2)))
        with self.assertRaises(QIRQRVMBackendError):
            compile_qir_function(lower_ast_function(ast))


if __name__ == "__main__":
    unittest.main()
