import unittest
from frontend.quar import ast_nodes as a
from qrvm.borrow_scoped_cfg import analyze_scoped_cfg
from qrvm.borrow_flow import BorrowFlow
from qrvm.ownership_analysis import OwnershipError


def decl(name, value=None):
    return a.VariableDeclaration('int', name, a.Integer(0) if value is None else value)


class ScopedCFGTests(unittest.TestCase):
    def test_empty(self):
        self.assertIsNotNone(analyze_scoped_cfg([]).analysis.at(1))

    def test_declaration(self):
        self.assertIsNotNone(analyze_scoped_cfg([decl('x')]).analysis.at(1))

    def test_assignment(self):
        analyze_scoped_cfg([decl('x'), a.Assignment('x', a.Integer(2))])

    def test_read(self):
        analyze_scoped_cfg([decl('x'), decl('y', a.Variable('x'))])

    def test_undefined_read(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([decl('x', a.Variable('missing'))])

    def test_undefined_write(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([a.Assignment('missing', a.Integer(1))])

    def test_if_locals_expire(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([a.IfStatement(a.Boolean(True), [decl('local')], []), decl('y', a.Variable('local'))])

    def test_else_locals_expire(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([a.IfStatement(a.Boolean(True), [], [decl('local')]), decl('y', a.Variable('local'))])

    def test_if_outer_available(self):
        analyze_scoped_cfg([decl('x'), a.IfStatement(a.Boolean(True), [a.Assignment('x', a.Integer(1))], [a.Assignment('x', a.Integer(2))]), decl('y', a.Variable('x'))])

    def test_nested_scopes(self):
        analyze_scoped_cfg([decl('x'), a.IfStatement(a.Boolean(True), [a.IfStatement(a.Boolean(True), [decl('inner')], [])], []), decl('y', a.Variable('x'))])

    def test_while_local_expires(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([a.WhileStatement(a.Boolean(True), [decl('local')]), decl('y', a.Variable('local'))])

    def test_while_repeated(self):
        result = analyze_scoped_cfg([decl('x'), a.WhileStatement(a.Boolean(True), [decl('tmp'), a.Assignment('x', a.Variable('tmp'))]), decl('y', a.Variable('x'))])
        self.assertGreater(result.analysis.processed, 0)

    def test_scope_budget(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([decl('x')], max_facts=1)

    def test_unsupported(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([a.ReturnStatement(a.Integer(1))])

    def test_shadowing_rejected(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_cfg([decl('x'), a.IfStatement(a.Boolean(True), [decl('x')], [])])


if __name__ == '__main__':
    unittest.main()
