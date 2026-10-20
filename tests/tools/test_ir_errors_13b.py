"""Differential error handling tests for the Quar IR to QRVM bridge."""
import unittest

from frontend.quar.ast_nodes import (Boolean, FunctionCall, Integer, String,
    ThrowStatement, TryCatchStatement, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.ir.model import IRThrow, IRTryCatch
from qrvm.compiler import QRVMCompiler
from qrvm.ir_bridge import compile_ir_statements
from qrvm.vm import QRVM, QuarPanic


class IRErrorTests(unittest.TestCase):
    def compare(self, program):
        direct = QRVMCompiler().compile(program)
        ir = tuple(lower_statement(statement) for statement in program)
        bridged = compile_ir_statements(ir)
        self.assertEqual(direct['instructions'], bridged['instructions'])
        return ir, direct, bridged

    def test_throw_caught(self):
        program = [VariableDeclaration('int', 'result', Integer(0)),
                   TryCatchStatement([ThrowStatement(String('failure'))], 'error',
                                     [VariableDeclaration('int', 'result', Integer(42))])]
        ir, direct, bridged = self.compare(program)
        self.assertIsInstance(ir[1], IRTryCatch)
        self.assertIsInstance(ir[1].try_body[0], IRThrow)
        vm_direct, vm_ir = QRVM(), QRVM()
        vm_direct.run(direct)
        vm_ir.run(bridged)
        self.assertEqual(vm_direct.variables, vm_ir.variables)
        self.assertEqual(vm_ir.variables['result'], 42)

    def test_assert_true(self):
        _, direct, bridged = self.compare([FunctionCall('assert', [Boolean(True)])])
        QRVM().run(direct)
        QRVM().run(bridged)

    def test_assert_false(self):
        _, direct, bridged = self.compare([FunctionCall('assert', [Boolean(False)])])
        for bytecode in (direct, bridged):
            with self.assertRaisesRegex(RuntimeError, 'Assertion failed'):
                QRVM().run(bytecode)

    def test_panic(self):
        _, direct, bridged = self.compare([FunctionCall('panic', [String('fatal')])])
        for bytecode in (direct, bridged):
            with self.assertRaisesRegex(QuarPanic, 'Panic: fatal'):
                QRVM().run(bytecode)

    def test_throw_uncaught(self):
        _, direct, bridged = self.compare([ThrowStatement(String('uncaught'))])
        for bytecode in (direct, bridged):
            with self.assertRaisesRegex(RuntimeError, 'uncaught'):
                QRVM().run(bytecode)


if __name__ == '__main__':
    unittest.main()
