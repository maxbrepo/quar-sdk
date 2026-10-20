"""Regression tests for conservative optional presence flow in QRVM compiler."""
import unittest
from frontend.quar.ast_nodes import VariableDeclaration, Variable, Integer, FunctionCall, IfStatement, Assignment
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def call(name, arg):
    return FunctionCall(name, [Variable(arg)])


class OptionalBranchFlowTests(unittest.TestCase):
    def test_present_then_branch_executes(self):
        program = [VariableDeclaration('int?', 'x', Integer(42)),
                   VariableDeclaration('int', 'result', Integer(0)),
                   IfStatement(call('present', 'x'),
                               [Assignment('result', call('unwrap', 'x'))], [])]
        vm = QRVM(); vm.run(QRVMCompiler().compile(program))
        self.assertEqual(vm.variables['result'], 42)

    def test_absent_else_branch_executes(self):
        program = [VariableDeclaration('int?', 'x', None),
                   VariableDeclaration('int', 'result', Integer(0)),
                   IfStatement(call('present', 'x'), [Assignment('result', Integer(1))],
                               [Assignment('result', Integer(2))])]
        vm = QRVM(); vm.run(QRVMCompiler().compile(program))
        self.assertEqual(vm.variables['result'], 2)

    def test_unwrap_in_known_absent_else_rejected(self):
        program = [VariableDeclaration('int?', 'x', None),
                   IfStatement(call('present', 'x'), [],
                               [VariableDeclaration('int', 'bad', call('unwrap', 'x'))])]
        with self.assertRaisesRegex(ValueError, 'definitely absent'):
            QRVMCompiler().compile(program)

    def test_no_global_rejection_for_unchecked_absence(self):
        program = [VariableDeclaration('int?', 'x', None),
                   VariableDeclaration('int', 'result', call('unwrap', 'x'))]
        # Existing runtime semantics are retained outside guarded branches.
        QRVMCompiler().compile(program)


if __name__ == '__main__':
    unittest.main()

class OptionalBranchMutationTests(unittest.TestCase):
    def test_assignment_in_else_invalidates_absence(self):
        program = [VariableDeclaration('int?', 'x', None),
                   VariableDeclaration('int', 'result', Integer(0)),
                   IfStatement(call('present', 'x'), [],
                               [Assignment('x', Integer(7)),
                                Assignment('result', call('unwrap', 'x'))])]
        vm = QRVM(); vm.run(QRVMCompiler().compile(program))
        self.assertEqual(vm.variables['result'], 7)
