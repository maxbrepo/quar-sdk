"""Execute canonical counter loops through both QIR lowering routes."""
import ctypes
import os
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, ForStatement,
    FunctionDefinition, FunctionParameter, Integer, ReturnStatement, Variable,
    VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class ForRecoveryTests(unittest.TestCase):
    def execute_both(self, function, cases):
        for route, qir in enumerate((lower_ast_function(function),
                                     lower_ir_function(lower_statement(function)))):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                source = os.path.join(directory, 'counter.c')
                library = os.path.join(directory, 'counter.so')
                with open(source, 'w', encoding='utf-8') as handle:
                    handle.write(emit_c_function(qir))
                subprocess.run(['cc', '-std=c99', '-shared', '-fPIC', '-Wno-unused-variable',
                                source, '-o', library], capture_output=True, check=True)
                compiled = getattr(ctypes.CDLL(library), function.name)
                compiled.argtypes = [ctypes.c_int32]
                compiled.restype = ctypes.c_int32
                self.assertEqual([compiled(arg) for arg, _ in cases],
                                 [expected for _, expected in cases])

    def make_function(self, comparison, step=1, direction=0):
        return FunctionDefinition('i32', 'for_counter',
            [FunctionParameter('i32', 'limit')], [
                VariableDeclaration('i32', 'counter', Integer(0)),
                VariableDeclaration('i32', 'total', Integer(0)),
                ForStatement('counter', Integer(0),
                    BinaryOperation(Variable('counter'), comparison, Variable('limit')),
                    [Assignment('total', BinaryOperation(Variable('total'), '+', Integer(1)))],
                    step, direction),
                ReturnStatement(Variable('total'))])

    def test_ascending_and_zero_iterations(self):
        self.execute_both(self.make_function('<', 2), [(0, 0), (1, 1), (5, 3)])

    def test_inclusive_ascending(self):
        self.execute_both(self.make_function('<=', 2), [(-1, 0), (0, 1), (4, 3)])

    def test_descending_counter(self):
        function = self.make_function('>', 2, -1)
        function.body[2].start = Integer(7)
        self.execute_both(function, [(7, 0), (6, 1), (0, 4)])

    def test_invalid_direction_rejected_in_both_routes(self):
        function = self.make_function('<', 1, -1)
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(function)
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(function))

    def test_zero_step_rejected_in_both_routes(self):
        function = self.make_function('<', 0)
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(function)
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(function))


if __name__ == '__main__':
    unittest.main()
