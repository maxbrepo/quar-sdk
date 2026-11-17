"""Execute the conservative while subset through both QIR routes."""
import ctypes
import os
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionDefinition,
    FunctionParameter, IfStatement, Integer, ReturnStatement, Variable,
    VariableDeclaration, WhileStatement)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class WhileRecoveryTests(unittest.TestCase):
    def run_both(self, function, cases):
        for route, qir in enumerate((lower_ast_function(function),
                                     lower_ir_function(lower_statement(function)))):
            with self.subTest(route=route), tempfile.TemporaryDirectory() as directory:
                source = os.path.join(directory, 'loop.c')
                library = os.path.join(directory, 'loop.so')
                with open(source, 'w', encoding='utf-8') as handle:
                    handle.write(emit_c_function(qir))
                subprocess.run(['cc', '-std=c99', '-shared', '-fPIC', '-Wno-unused-variable',
                                source, '-o', library], capture_output=True, check=True)
                compiled = getattr(ctypes.CDLL(library), function.name)
                compiled.argtypes = [ctypes.c_int32]
                compiled.restype = ctypes.c_int32
                self.assertEqual([compiled(arg) for arg, _ in cases],
                                 [expected for _, expected in cases])

    def test_zero_and_multiple_iterations(self):
        function = FunctionDefinition('i32', 'count_loop', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'count', Integer(0)),
            WhileStatement(BinaryOperation(Variable('count'), '<', Variable('limit')), [
                Assignment('count', BinaryOperation(Variable('count'), '+', Integer(1)))]),
            ReturnStatement(Variable('count'))])
        self.run_both(function, [(0, 0), (1, 1), (5, 5)])

    def test_conditional_body_assignment(self):
        function = FunctionDefinition('i32', 'sum_loop', [FunctionParameter('i32', 'limit')], [
            VariableDeclaration('i32', 'count', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(BinaryOperation(Variable('count'), '<', Variable('limit')), [
                IfStatement(BinaryOperation(Variable('count'), '<', Integer(3)), [
                    Assignment('total', BinaryOperation(Variable('total'), '+', Integer(2)))], []),
                Assignment('count', BinaryOperation(Variable('count'), '+', Integer(1)))]),
            ReturnStatement(Variable('total'))])
        self.run_both(function, [(0, 0), (2, 4), (5, 6)])


if __name__ == '__main__':
    unittest.main()
