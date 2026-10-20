"""Chapter 15.20: conservative boolean validation for QRVM conditions."""
import unittest
from frontend.quar.ast_nodes import (VariableDeclaration, Variable, Integer, Boolean,
    BinaryOperation, IfStatement, FunctionCall, FunctionDefinition, ReturnStatement)
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def run(program):
    vm = QRVM()
    vm.run(QRVMCompiler().compile(program))
    return vm


class OptionalBooleanConditionsTests(unittest.TestCase):
    def test_and_rejects_integer_left(self):
        with self.assertRaisesRegex(ValueError, 'requires bool'):
            QRVMCompiler().compile([IfStatement(BinaryOperation(Integer(1), 'and', Boolean(True)), [], [])])

    def test_or_rejects_integer_right_even_if_skipped(self):
        with self.assertRaisesRegex(ValueError, 'requires bool'):
            QRVMCompiler().compile([IfStatement(BinaryOperation(Boolean(True), 'or', Integer(1)), [], [])])

    def test_rejects_declared_integer_variable(self):
        with self.assertRaisesRegex(ValueError, 'requires bool'):
            QRVMCompiler().compile([VariableDeclaration('int', 'n', Integer(1)),
                IfStatement(BinaryOperation(Variable('n'), 'and', Boolean(True)), [], [])])

    def test_rejects_optional_variable_as_condition(self):
        with self.assertRaisesRegex(ValueError, 'requires bool'):
            QRVMCompiler().compile([VariableDeclaration('int?', 'n', Integer(1)),
                IfStatement(Variable('n'), [], [])])

    def test_accepts_bool_variables(self):
        vm = run([VariableDeclaration('bool', 'flag', Boolean(True)),
            VariableDeclaration('bool', 'result', Boolean(False)),
            IfStatement(BinaryOperation(Variable('flag'), 'and', Boolean(True)),
                [__import__('frontend.quar.ast_nodes', fromlist=['Assignment']).Assignment('result', Boolean(True))], [])])
        self.assertTrue(vm.variables['result'])

    def test_unknown_expression_remains_runtime_checked(self):
        # Unknown types are not guessed by the compiler.
        QRVMCompiler().compile([IfStatement(Variable('external'), [], [])])

    def test_function_scope_does_not_leak_types(self):
        fn = FunctionDefinition('void', 'f', [], [VariableDeclaration('int', 'v', Integer(1))])
        QRVMCompiler().compile([fn, VariableDeclaration('bool', 'v', Boolean(True)),
            IfStatement(Variable('v'), [], [])])

    def test_existing_short_circuit_still_works(self):
        cond = BinaryOperation(FunctionCall('present', [Variable('x')]), 'and',
            BinaryOperation(FunctionCall('unwrap', [Variable('x')]), '>', Integer(0)))
        run([VariableDeclaration('int?', 'x', None), IfStatement(cond, [], [])])


if __name__ == '__main__':
    unittest.main()
