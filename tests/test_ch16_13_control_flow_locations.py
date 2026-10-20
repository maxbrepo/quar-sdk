"""Source-location regression tests for Control Flow Inspector."""
import unittest
from frontend.quar import ast_nodes as a
from qrvm.inspector import inspect_program
from qrvm.inspector_control_flow import inspect_control_flow


def function(body):
    return a.FunctionDefinition('int', 'example', [], body)


class ControlFlowLocationTests(unittest.TestCase):
    def test_unreachable_statement_has_own_span(self):
        unreachable = a.Assignment('x', a.Integer(2))
        unreachable.start, unreachable.end = (5, 3), (5, 8)
        result = inspect_control_flow(function([a.ReturnStatement(a.Integer(1)), unreachable]), path='demo.vq')
        finding = next(d for d in result.diagnostics if d.code == 'QI-CFG-002')
        self.assertEqual((finding.location.line, finding.location.column), (5, 3))
        self.assertEqual(finding.source_range.end.column, 8)

    def test_constant_condition_points_to_expression(self):
        condition = a.Boolean(True)
        condition.start, condition.end = (2, 5), (2, 9)
        result = inspect_control_flow(function([a.IfStatement(condition, [a.ReturnStatement(a.Integer(1))], [])]), path='demo.vq')
        finding = next(d for d in result.diagnostics if d.code == 'QI-CFG-003')
        self.assertEqual(finding.location.column, 5)

    def test_missing_return_points_to_function(self):
        item = function([])
        item.start, item.end = (1, 1), (3, 2)
        finding = inspect_control_flow(item, path='demo.vq').diagnostics[0]
        self.assertEqual(finding.location.line, 1)
        self.assertEqual(finding.source_range.end.line, 3)

    def test_without_path_remains_backward_compatible(self):
        item = function([])
        item.start, item.end = (1, 1), (3, 2)
        self.assertIsNone(inspect_control_flow(item).diagnostics[0].location)

    def test_coordinator_forwards_path(self):
        item = function([])
        item.start, item.end = (2, 1), (4, 2)
        report = inspect_program(item.body, function=item, enabled=('control_flow',), path='demo.vq')
        self.assertEqual(report.result.diagnostics[0].location.line, 2)


if __name__ == '__main__':
    unittest.main()
