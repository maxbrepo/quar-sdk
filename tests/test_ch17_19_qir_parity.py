"""Independent lowering-route parity checks and actual C99 execution tests."""
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionDefinition,
    FunctionParameter, Integer, ReturnStatement, Variable, VariableDeclaration, IfStatement)
from frontend.quar.qir.parity import compare_ast_qir_routes
from frontend.quar.qir.ast_lowering import QIRASTLoweringError
from frontend.quar.qir.c_backend import emit_c_function


class QIRParityTests(unittest.TestCase):
    def make_function(self, body, parameters=(), result="int"):
        return FunctionDefinition(result, "compute", list(parameters), list(body))

    def test_constant(self):
        report = compare_ast_qir_routes(self.make_function([ReturnStatement(Integer(42))]))
        self.assertTrue(report.equivalent, report.differences)

    def test_parameters(self):
        f = self.make_function([ReturnStatement(BinaryOperation(Variable("x"), "+", Integer(3)))],
                               [FunctionParameter("int", "x")])
        self.assertTrue(compare_ast_qir_routes(f).equivalent)

    def test_reassignment(self):
        f = self.make_function([VariableDeclaration("int", "x", Integer(4)),
            Assignment("x", BinaryOperation(Variable("x"), "*", Integer(5))),
            ReturnStatement(Variable("x"))])
        self.assertTrue(compare_ast_qir_routes(f).equivalent)

    def test_alias(self):
        f = self.make_function([ReturnStatement(Variable("x"))],
                               [FunctionParameter("Counter", "x")], "Counter")
        self.assertTrue(compare_ast_qir_routes(f, type_aliases={"Counter": "long"}).equivalent)

    def test_unsupported_control_flow_fails_closed(self):
        f = self.make_function([IfStatement(Integer(1), [], []), ReturnStatement(Integer(0))])
        with self.assertRaises(QIRASTLoweringError):
            compare_ast_qir_routes(f)

    def test_source_unchanged(self):
        f = self.make_function([ReturnStatement(Integer(1))])
        before = repr(f)
        compare_ast_qir_routes(f)
        self.assertEqual(repr(f), before)

    def test_detects_different_return_value(self):
        from frontend.quar.qir.model import QBlock, QFunction, QReturn
        f = self.make_function([ReturnStatement(BinaryOperation(Integer(1), "+", Integer(2)))])
        actual = compare_ast_qir_routes(f)
        changed = QFunction(actual.bridged.name, actual.bridged.return_type,
                            actual.bridged.parameters, (QBlock("entry", actual.bridged.blocks[0].instructions,
                            QReturn(actual.bridged.blocks[0].instructions[0].result)),))
        from frontend.quar.qir.parity import _signature
        self.assertNotEqual(_signature(actual.direct), _signature(changed))

    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_both_qir_routes_compile_and_run(self):
        f = self.make_function([ReturnStatement(BinaryOperation(Variable("x"), "+", Integer(7)))],
                               [FunctionParameter("int", "x")])
        report = compare_ast_qir_routes(f)
        self.assertTrue(report.equivalent)
        for qir in (report.direct, report.bridged):
            with self.subTest(route=qir.blocks[0].instructions[0].result.name):
                with tempfile.TemporaryDirectory() as directory:
                    source = os.path.join(directory, "check.c")
                    binary = os.path.join(directory, "check")
                    with open(source, "w", encoding="utf-8") as output:
                        output.write(emit_c_function(qir))
                        output.write("\nint main(void) { return compute(35) == 42 ? 0 : 1; }\n")
                    subprocess.run(["cc", "-std=c99", "-O0", source, "-o", binary],
                                   check=True, capture_output=True, timeout=15)
                    result = subprocess.run([binary], capture_output=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
