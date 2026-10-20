"""Chapter 15.19: optional flow facts and short-circuit evaluation."""
import unittest
from frontend.quar.ast_nodes import (VariableDeclaration, Variable, Integer,
    Boolean, FunctionCall, IfStatement, Assignment, BinaryOperation)
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def present(name):
    return FunctionCall('present', [Variable(name)])


def unwrap(name):
    return FunctionCall('unwrap', [Variable(name)])


def run(program):
    vm = QRVM()
    vm.run(QRVMCompiler().compile(program))
    return vm


class CompoundOptionalConditionsTests(unittest.TestCase):
    def test_and_skips_absent_unwrap(self):
        cond = BinaryOperation(present('x'), 'and', BinaryOperation(unwrap('x'), '>', Integer(0)))
        vm = run([VariableDeclaration('int?', 'x', None),
                  VariableDeclaration('int', 'result', Integer(0)),
                  IfStatement(cond, [Assignment('result', Integer(1))], [])])
        self.assertEqual(vm.variables['result'], 0)

    def test_and_evaluates_present_unwrap(self):
        cond = BinaryOperation(present('x'), 'and', BinaryOperation(unwrap('x'), '>', Integer(0)))
        vm = run([VariableDeclaration('int?', 'x', Integer(3)),
                  VariableDeclaration('int', 'result', Integer(0)),
                  IfStatement(cond, [Assignment('result', Integer(1))], [])])
        self.assertEqual(vm.variables['result'], 1)

    def test_or_skips_right_when_present(self):
        cond = BinaryOperation(present('x'), 'or', BinaryOperation(unwrap('y'), '>', Integer(0)))
        vm = run([VariableDeclaration('int?', 'x', Integer(1)),
                  VariableDeclaration('int?', 'y', None),
                  VariableDeclaration('int', 'result', Integer(0)),
                  IfStatement(cond, [Assignment('result', Integer(1))], [])])
        self.assertEqual(vm.variables['result'], 1)

    def test_and_true_proves_both_present(self):
        cond = BinaryOperation(present('x'), 'and', present('y'))
        vm = run([VariableDeclaration('int?', 'x', Integer(2)),
                  VariableDeclaration('int?', 'y', Integer(3)),
                  VariableDeclaration('int', 'result', Integer(0)),
                  IfStatement(cond, [Assignment('result', unwrap('y'))], [])])
        self.assertEqual(vm.variables['result'], 3)

    def test_or_false_proves_both_absent(self):
        cond = BinaryOperation(present('x'), 'or', present('y'))
        program = [VariableDeclaration('int?', 'x', None),
                   VariableDeclaration('int?', 'y', None),
                   IfStatement(cond, [], [VariableDeclaration('int', 'bad', unwrap('y'))])]
        with self.assertRaisesRegex(ValueError, 'definitely absent'):
            QRVMCompiler().compile(program)

    def test_and_false_does_not_imply_both_absent(self):
        cond = BinaryOperation(present('x'), 'and', present('y'))
        QRVMCompiler().compile([VariableDeclaration('int?', 'x', None),
            VariableDeclaration('int?', 'y', Integer(1)),
            IfStatement(cond, [], [VariableDeclaration('int', 'ok', unwrap('y'))])])

    def test_or_right_is_checked_under_left_absence(self):
        cond = BinaryOperation(present('x'), 'or', BinaryOperation(unwrap('x'), '>', Integer(0)))
        with self.assertRaisesRegex(ValueError, 'definitely absent'):
            QRVMCompiler().compile([VariableDeclaration('int?', 'x', None), IfStatement(cond, [], [])])


if __name__ == '__main__':
    unittest.main()
