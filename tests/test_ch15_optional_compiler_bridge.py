"""Chapter 15.14: optional declarations compiled to QRVM opcodes."""
import unittest

from frontend.quar.ast_nodes import Integer, VariableDeclaration, Variable
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class OptionalCompilerBridgeTests(unittest.TestCase):
    def test_present_integer_emits_wrapper(self):
        code = QRVMCompiler().compile_statement(VariableDeclaration("int?", "x", Integer(0)))
        self.assertEqual([op for op, _ in code], [OpCode.PUSH_INT, OpCode.OPTIONAL_SOME, OpCode.STORE])

    def test_absent_optional_emits_none(self):
        code = QRVMCompiler().compile_statement(VariableDeclaration("int?", "x", None))
        self.assertEqual(code, [(OpCode.OPTIONAL_NONE, None), (OpCode.STORE, "x")])

    def test_nonoptional_declaration_is_unchanged(self):
        code = QRVMCompiler().compile_statement(VariableDeclaration("int", "x", Integer(0)))
        self.assertEqual([op for op, _ in code], [OpCode.PUSH_INT, OpCode.STORE])

    def test_present_roundtrip_in_vm(self):
        compiler = QRVMCompiler()
        code = compiler.compile_statement(VariableDeclaration("int?", "x", Integer(42)))
        code += [(OpCode.LOAD, "x"), (OpCode.OPTIONAL_UNWRAP, None)]
        vm = QRVM()
        vm.run(code)
        self.assertEqual(vm.stack, [42])

    def test_absent_presence_in_vm(self):
        compiler = QRVMCompiler()
        code = compiler.compile_statement(VariableDeclaration("int?", "x", None))
        code += [(OpCode.LOAD, "x"), (OpCode.OPTIONAL_IS_PRESENT, None)]
        vm = QRVM()
        vm.run(code)
        self.assertEqual(vm.stack, [False])


if __name__ == "__main__":
    unittest.main()
