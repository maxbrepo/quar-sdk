"""Tests for terminal and editor diagnostic formatting."""
import json
import unittest
from frontend.quar.ast_nodes import FunctionDefinition, ReturnStatement, Integer
from qrvm.inspector_diagnostics import Diagnostic, Severity, SourceLocation
from qrvm.inspector_format import format_diagnostic, diagnostic_record, pipeline_json
from qrvm.inspector_pipeline import inspect_validated_program, format_pipeline_inspection


class DiagnosticFormatTests(unittest.TestCase):
    def test_location(self):
        finding = Diagnostic('QI-TST-001', Severity.ERROR, 'bad index', 'bounds', SourceLocation('file.vq', 3, 5))
        self.assertIn('file.vq:3:5', format_diagnostic(finding))

    def test_missing_location_is_null(self):
        finding = Diagnostic('QI-TST-002', Severity.WARNING, 'uncertain', 'numeric')
        self.assertIsNone(diagnostic_record(finding)['location'])

    def test_suggestion(self):
        finding = Diagnostic('QI-TST-003', Severity.HINT, 'simplify', 'values', suggestion='use constant')
        self.assertIn('use constant', format_diagnostic(finding))

    def test_scope(self):
        finding = Diagnostic('QI-TST-004', Severity.INFO, 'unused', 'scopes')
        self.assertEqual(diagnostic_record(finding, scope='main')['scope'], 'main')

    def test_pipeline_json(self):
        program = [FunctionDefinition('int', 'answer', [], [ReturnStatement(Integer(42))])]
        result = json.loads(pipeline_json(inspect_validated_program(program)))
        self.assertEqual(result['schema_version'], 1)
        self.assertFalse(result['blocking'])
        self.assertEqual(result['reports'][0]['scope'], 'answer')
        self.assertTrue(result['reports'][0]['passes'])

    def test_pipeline_terminal_compatibility(self):
        self.assertIn('Quar Inspector:', format_pipeline_inspection(inspect_validated_program([])))


if __name__ == '__main__':
    unittest.main()
