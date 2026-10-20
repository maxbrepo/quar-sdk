"""Regression tests for the unified Inspector coordinator."""
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector import combine_inspections, inspect_program
from qrvm.inspector_diagnostics import AnalysisStatus, Diagnostic, InspectionResult, Severity


class InspectorIntegrationTests(unittest.TestCase):
    def test_empty_selected_passes(self):
        self.assertEqual(inspect_program([], enabled=[]).result.status, AnalysisStatus.PASS)

    def test_unknown_dominates_pass(self):
        merged = combine_inspections([InspectionResult(AnalysisStatus.PASS), InspectionResult(AnalysisStatus.UNKNOWN)])
        self.assertEqual(merged.status, AnalysisStatus.UNKNOWN)

    def test_unsupported_dominates_unknown(self):
        merged = combine_inspections([InspectionResult(AnalysisStatus.UNKNOWN), InspectionResult(AnalysisStatus.UNSUPPORTED)])
        self.assertEqual(merged.status, AnalysisStatus.UNSUPPORTED)

    def test_fail_dominates_unsupported(self):
        merged = combine_inspections([InspectionResult(AnalysisStatus.UNSUPPORTED), InspectionResult(AnalysisStatus.FAIL)])
        self.assertEqual(merged.status, AnalysisStatus.FAIL)

    def test_diagnostic_deduplication(self):
        d = Diagnostic('QI-TEST', Severity.WARNING, 'Warning', 'test')
        result = combine_inspections([InspectionResult(AnalysisStatus.PASS, (d,)), InspectionResult(AnalysisStatus.PASS, (d,))])
        self.assertEqual(result.diagnostics, (d,))

    def test_selective_bounds_error(self):
        body = [ast.ArrayDeclaration('i32', 'a', 2), ast.ArrayAccess('a', ast.Integer(2))]
        report = inspect_program(body, enabled=('bounds',))
        self.assertEqual(report.result.status, AnalysisStatus.FAIL)
        self.assertEqual(report.passes[0][0], 'bounds')

    def test_control_flow_requires_function(self):
        report = inspect_program([], enabled=('control_flow',))
        self.assertEqual(report.result.status, AnalysisStatus.UNSUPPORTED)

    def test_control_flow_function(self):
        fn = ast.FunctionDefinition('int', 'f', [], [ast.ReturnStatement(ast.Integer(1))])
        report = inspect_program(fn.body, function=fn, enabled=('control_flow',))
        self.assertEqual(report.result.status, AnalysisStatus.PASS)

    def test_invalid_pass_rejected(self):
        with self.assertRaises(ValueError):
            inspect_program([], enabled=('not_a_pass',))

    def test_duplicate_pass_rejected(self):
        with self.assertRaises(ValueError):
            inspect_program([], enabled=('bounds', 'bounds'))


if __name__ == '__main__':
    unittest.main()
