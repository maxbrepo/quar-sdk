"""Array boundaries: unsupported layouts and invalid accesses fail closed."""
import unittest

from frontend.quar.ast_nodes import (ArrayAccess, ArrayAssignment, ArrayDeclaration,
    FunctionDefinition, Integer, ReturnStatement, VariableDeclaration)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function, QIRASTLoweringError
from frontend.quar.qir.legacy_bridge import lower_ir_function, QIRBridgeError


class ArrayBoundaryTests(unittest.TestCase):
    def assert_rejected_both(self, statements):
        function = FunctionDefinition('i32', 'array_boundary', [], statements)
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(function)
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(function))

    def test_dynamic_array_is_not_supported(self):
        self.assert_rejected_both([
            ArrayDeclaration('i32', 'items', 3, [Integer(2), Integer(4), Integer(6)], dynamic=True),
            ReturnStatement(Integer(0))])

    def test_undeclared_array_access_is_rejected(self):
        self.assert_rejected_both([
            VariableDeclaration('i32', 'total', ArrayAccess('items', Integer(0))),
            ReturnStatement(Integer(0))])

    def test_undeclared_array_assignment_is_rejected(self):
        self.assert_rejected_both([
            ArrayAssignment('items', Integer(0), Integer(7)),
            ReturnStatement(Integer(0))])

    def test_multidimensional_access_is_rejected(self):
        self.assert_rejected_both([
            ArrayDeclaration('i32', 'items', 3, [Integer(2), Integer(4), Integer(6)]),
            ReturnStatement(ArrayAccess('items', Integer(0), Integer(0)))])


if __name__ == '__main__':
    unittest.main()
