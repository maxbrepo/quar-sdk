"""Executable parity tests for fixed i32 arrays lowered from both source routes."""
import ctypes
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.ast_nodes import (ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment,
    BinaryOperation, ForStatement, FunctionDefinition, Integer, ReturnStatement, Variable, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function, QIRASTLoweringError
from frontend.quar.qir.legacy_bridge import lower_ir_function, QIRBridgeError
from frontend.quar.qir.c_backend import emit_c_function


class SourceArrayIntegrationTests(unittest.TestCase):
    def run_both(self, body, expected):
        function = FunctionDefinition('i32', 'array_source_demo', [], body)
        for qir in (lower_ast_function(function), lower_ir_function(lower_statement(function))):
            source = emit_c_function(qir)
            with tempfile.TemporaryDirectory() as tmp:
                c_path = Path(tmp) / 'test.c'
                so_path = Path(tmp) / 'test.so'
                c_path.write_text(source)
                subprocess.run(['cc', '-std=c99', '-shared', '-fPIC', str(c_path), '-o', str(so_path)], check=True, capture_output=True)
                self.assertEqual(ctypes.CDLL(str(so_path)).array_source_demo(), expected)

    def test_initialized_array_read(self):
        self.run_both([ArrayDeclaration('i32', 'items', 3, [Integer(2), Integer(4), Integer(6)]),
                       ReturnStatement(ArrayAccess('items', Integer(1)))], 4)

    def test_array_write_and_read(self):
        self.run_both([ArrayDeclaration('i32', 'items', 3, [Integer(2), Integer(4), Integer(6)]),
                       ArrayAssignment('items', Integer(1), Integer(17)),
                       ReturnStatement(ArrayAccess('items', Integer(1)))], 17)

    def test_array_sum_with_for(self):
        self.run_both([VariableDeclaration('i32', 'i', Integer(0)),
                       VariableDeclaration('i32', 'total', Integer(0)),
                       ArrayDeclaration('i32', 'items', 3, [Integer(2), Integer(4), Integer(6)]),
                       ForStatement('i', Integer(0), BinaryOperation(Variable('i'), '<', Integer(3)),
                           [Assignment('total', BinaryOperation(Variable('total'), '+', ArrayAccess('items', Variable('i'))))]),
                       ReturnStatement(Variable('total'))], 12)

    def test_unsupported_dynamic_array_fails_closed(self):
        function = FunctionDefinition('i32', 'array_source_demo', [], [
            ArrayDeclaration('i32', 'items', 3, [Integer(2), Integer(4), Integer(6)], dynamic=True),
            ReturnStatement(Integer(0))])
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(function)
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(function))


if __name__ == '__main__':
    unittest.main()
