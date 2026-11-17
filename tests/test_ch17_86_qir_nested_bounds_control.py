"""Runtime bounds enforcement after nested-loop index updates on both QIR routes."""
import unittest

from frontend.quar.ast_nodes import (
    ArrayAccess, ArrayAssignment, ArrayDeclaration, Assignment, BinaryOperation,
    BreakStatement, ContinueStatement, ForStatement, FunctionCall, IfStatement,
    Integer, ReturnStatement, String, Variable, VariableDeclaration, WhileStatement,
)
from test_ch17_85_qir_unicode_array_bounds import UnicodeArrayBoundsTests
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def var(name):
    return Variable(name)


def op(left, operator, right):
    return BinaryOperation(left, operator, right)


def scalar(text, index):
    return FunctionCall('__qir_utf8_scalar_at', [text, index])


def length(text):
    return FunctionCall('__qir_utf8_scalar_len', [text])


class NestedBoundsControlTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both
    check_routes = UnicodeArrayBoundsTests.check_routes

    def test_nested_loop_valid_dynamic_indices(self):
        self.run_both([
            VariableDeclaration('string', 'text', String('aé😀')),
            ArrayDeclaration('i32', 'items', 3, [Integer(0), Integer(0), Integer(0)]),
            VariableDeclaration('i32', 'outer', Integer(0)),
            VariableDeclaration('i32', 'inner', Integer(0)),
            ForStatement('outer', Integer(0), op(var('outer'), '<', Integer(2)), [
                ForStatement('inner', Integer(0), op(var('inner'), '<', length(var('text'))), [
                    ArrayAssignment('items', var('inner'), op(ArrayAccess('items', var('inner')), '+',
                        scalar(var('text'), var('inner')))),
                ]),
            ]),
            ReturnStatement(ArrayAccess('items', Integer(1))),
        ], 2 * ord('é'))

    def test_continue_prevents_invalid_array_access(self):
        self.run_both([
            ArrayDeclaration('i32', 'items', 2, [Integer(7), Integer(11)]),
            VariableDeclaration('i32', 'index', Integer(0)),
            WhileStatement(op(var('index'), '<', Integer(3)), [
                IfStatement(op(var('index'), '==', Integer(2)), [BreakStatement()], []),
                Assignment('index', op(var('index'), '+', Integer(1))),
            ]),
            ReturnStatement(ArrayAccess('items', op(var('index'), '-', Integer(1)))),
        ], 11)

    def test_nested_loop_out_of_bounds_array_traps(self):
        self.check_routes([
            ArrayDeclaration('i32', 'items', 2, [Integer(3), Integer(5)]),
            VariableDeclaration('i32', 'outer', Integer(0)),
            VariableDeclaration('i32', 'inner', Integer(0)),
            ForStatement('outer', Integer(0), op(var('outer'), '<', Integer(2)), [
                ForStatement('inner', Integer(0), op(var('inner'), '<', Integer(2)), [
                    ArrayAssignment('items', op(var('outer'), '+', var('inner')), Integer(9)),
                ]),
            ]),
            ReturnStatement(Integer(0)),
        ], 'trap')

    def test_unicode_index_modified_inside_loop_traps(self):
        self.check_routes([
            VariableDeclaration('string', 'text', String('aé😀')),
            VariableDeclaration('i32', 'index', Integer(0)),
            WhileStatement(op(var('index'), '<', length(var('text'))), [
                Assignment('index', op(var('index'), '+', Integer(3))),
            ]),
            ReturnStatement(scalar(var('text'), var('index'))),
        ], 'trap')


if __name__ == '__main__':
    unittest.main()
