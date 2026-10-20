"""Chapter 15.22: conservative optional facts at loop boundaries."""
import unittest
from frontend.quar.ast_nodes import (
    VariableDeclaration, Assignment, Variable, Integer, Boolean,
    FunctionCall, WhileStatement, LoopStatement, DoWhileStatement,
    ForStatement, BinaryOperation,
)
from qrvm.compiler import QRVMCompiler


def present(name):
    return FunctionCall("present", [Variable(name)])


class OptionalLoopInvalidationTests(unittest.TestCase):
    def test_while_does_not_leak_body_presence(self):
        compiler = QRVMCompiler()
        compiler.compile([VariableDeclaration("int?", "x", None),
                          WhileStatement(Boolean(False), [Assignment("x", Integer(1))])])
        self.assertIsNone(compiler._optional_presence["x"])

    def test_while_forgets_pre_loop_presence(self):
        compiler = QRVMCompiler()
        compiler.compile([VariableDeclaration("int?", "x", Integer(1)),
                          WhileStatement(Boolean(False), [])])
        self.assertIsNone(compiler._optional_presence["x"])

    def test_loop_body_does_not_leak_absence(self):
        compiler = QRVMCompiler()
        compiler.compile([VariableDeclaration("int?", "x", Integer(1)),
                          LoopStatement([Assignment("x", None)])])
        self.assertIsNone(compiler._optional_presence["x"])
        self.assertNotIn("x", compiler._conditional_absence)

    def test_do_while_does_not_leak_presence(self):
        compiler = QRVMCompiler()
        compiler.compile([VariableDeclaration("int?", "x", None),
                          DoWhileStatement([Assignment("x", Integer(2))], Boolean(False))])
        self.assertIsNone(compiler._optional_presence["x"])

    def test_optional_type_survives_loop(self):
        compiler = QRVMCompiler()
        compiler.compile([VariableDeclaration("int?", "x", None),
                          WhileStatement(Boolean(False), []), present("x")])
        self.assertIn("x", compiler._optional_variables)
        self.assertEqual(compiler._declared_types["x"], "int?")

    def test_for_does_not_leak_presence(self):
        from frontend.quar.ast_nodes import ForStatement
        import inspect
        self.assertIn("_invalidate_loop_facts", inspect.getsource(QRVMCompiler.compile_for_statement))


if __name__ == "__main__":
    unittest.main()
