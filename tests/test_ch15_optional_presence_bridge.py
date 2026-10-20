"""Chapter 15.16: internal optional presence/unwrap lowering."""
import unittest
from frontend.quar.ast_nodes import (VariableDeclaration, Variable, Integer, FunctionCall,
                                     IfStatement, Assignment)
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM, QuarOptionalError
from qrvm.instructions import OpCode


def call(name, *args):
    return FunctionCall(name, list(args))


class OptionalPresenceBridgeTests(unittest.TestCase):
    def execute(self, statements):
        code = QRVMCompiler().compile(statements)
        vm = QRVM()
        vm.run(code)
        return vm

    def test_present_value(self):
        vm = self.execute([VariableDeclaration('int?', 'x', Integer(42)),
                           VariableDeclaration('bool', 'found', call('present', Variable('x')))])
        self.assertIs(vm.variables['found'], True)

    def test_absent_value(self):
        vm = self.execute([VariableDeclaration('int?', 'x', None),
                           VariableDeclaration('bool', 'found', call('present', Variable('x')))])
        self.assertIs(vm.variables['found'], False)

    def test_unwrap_present(self):
        vm = self.execute([VariableDeclaration('int?', 'x', Integer(42)),
                           VariableDeclaration('int', 'result', call('unwrap', Variable('x')))])
        self.assertEqual(vm.variables['result'], 42)

    def test_unwrap_absent_raises(self):
        with self.assertRaises(QuarOptionalError):
            self.execute([VariableDeclaration('int?', 'x', None),
                          VariableDeclaration('int', 'result', call('unwrap', Variable('x')))])

    def test_reject_nonoptional(self):
        with self.assertRaises(ValueError):
            QRVMCompiler().compile([VariableDeclaration('int', 'x', Integer(1)),
                                    VariableDeclaration('bool', 'ok', call('present', Variable('x')))])

    def test_reject_wrong_arity(self):
        with self.assertRaises(ValueError):
            QRVMCompiler().compile([VariableDeclaration('int?', 'x', None),
                                    VariableDeclaration('bool', 'ok', call('present'))])

    def test_emits_expected_opcode(self):
        code = QRVMCompiler().compile([VariableDeclaration('int?', 'x', Integer(2)),
                                       VariableDeclaration('int', 'y', call('unwrap', Variable('x')))])
        self.assertIn(OpCode.OPTIONAL_UNWRAP, [op for op, _ in code['instructions']])


if __name__ == '__main__':
    unittest.main()
