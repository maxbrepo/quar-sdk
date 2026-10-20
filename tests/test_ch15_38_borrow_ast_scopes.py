import unittest
from frontend.quar import ast_nodes as a
from qrvm.borrow_ast_scopes import analyze_scoped_ast
from qrvm.borrow_flow import BorrowFlow
from qrvm.ownership_analysis import OwnershipError


def dec(name, value=1):
    return a.VariableDeclaration('int', name, a.Integer(value))


class ScopedASTTests(unittest.TestCase):
    def test_plain_declaration(self):
        self.assertIn('x', analyze_scoped_ast([dec('x')]).flow.paths[0].lifetime.declared)

    def test_if_local_does_not_escape(self):
        result = analyze_scoped_ast([dec('x'), a.IfStatement(a.Variable('x'), [dec('local')], [])])
        self.assertTrue(all('local' not in p.lifetime.declared for p in result.flow.paths))

    def test_if_local_unavailable_after_branch(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_ast([dec('x'), a.IfStatement(a.Variable('x'), [dec('local')], []), a.Assignment('local', a.Integer(2))])

    def test_same_name_in_sibling_branches(self):
        result = analyze_scoped_ast([dec('x'), a.IfStatement(a.Variable('x'), [dec('temp')], [dec('temp')])])
        self.assertEqual(len(result.flow.paths), 2)

    def test_outer_write_from_branch(self):
        analyze_scoped_ast([dec('x'), a.IfStatement(a.Variable('x'), [a.Assignment('x', a.Integer(2))], [])])

    def test_branch_local_shadowing_fails_closed(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_ast([dec('x'), a.IfStatement(a.Variable('x'), [dec('x')], [])])

    def test_while_local_expires_each_iteration(self):
        result = analyze_scoped_ast([dec('x'), a.WhileStatement(a.Variable('x'), [dec('temp')])])
        self.assertGreater(result.loop_applications, 0)
        self.assertTrue(all('temp' not in p.lifetime.declared for p in result.flow.paths))

    def test_while_local_unavailable_after_loop(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_ast([dec('x'), a.WhileStatement(a.Variable('x'), [dec('temp')]), a.Assignment('temp', a.Integer(1))])

    def test_nested_scopes(self):
        nested = a.IfStatement(a.Variable('x'), [dec('inner')], [])
        result = analyze_scoped_ast([dec('x'), a.IfStatement(a.Variable('x'), [dec('outer'), nested], [])])
        self.assertTrue(all(set(p.lifetime.declared) == {'x'} for p in result.flow.paths))

    def test_borrow_conflict_in_branch(self):
        initial = BorrowFlow.empty().declare('x').borrow('x', 'ref')
        with self.assertRaisesRegex(OwnershipError, 'conflict'):
            analyze_scoped_ast([a.IfStatement(a.Variable('x'), [a.Assignment('x', a.Integer(3))], [])], initial)

    def test_borrow_conflict_in_loop(self):
        initial = BorrowFlow.empty().declare('x').borrow('x', 'ref')
        with self.assertRaisesRegex(OwnershipError, 'conflict'):
            analyze_scoped_ast([a.WhileStatement(a.Variable('x'), [a.Assignment('x', a.Integer(3))])], initial)

    def test_unsupported_fails_closed(self):
        with self.assertRaisesRegex(OwnershipError, 'Unsupported'):
            analyze_scoped_ast([a.FunctionCall('f', [])])

    def test_invalid_budget(self):
        with self.assertRaises(OwnershipError):
            analyze_scoped_ast([], max_states=0)

    def test_existing_root_scope_preserved(self):
        result = analyze_scoped_ast([a.IfStatement(a.Variable('x'), [dec('tmp')], [])], BorrowFlow.empty().declare('x'))
        self.assertTrue(all(p.lifetime.scopes == ('root',) for p in result.flow.paths))


if __name__ == '__main__':
    unittest.main()
