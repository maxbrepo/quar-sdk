"""Tests for opt-in Inspector compiler pipeline integration."""
import unittest
from unittest.mock import patch
import main
from frontend.quar.ast_nodes import FunctionDefinition, ReturnStatement, Integer
from qrvm.inspector_pipeline import inspect_validated_program, format_pipeline_inspection
from qrvm.inspector_diagnostics import AnalysisStatus


class InspectorPipelineTests(unittest.TestCase):
    def test_flag_off(self):
        self.assertEqual(main.extract_inspector_flag(['-f', 'a.vq']), (['-f', 'a.vq'], False))

    def test_flag_on(self):
        self.assertEqual(main.extract_inspector_flag(['--inspect', '-f', 'a.vq']), (['-f', 'a.vq'], True))

    def test_duplicate_flag(self):
        with self.assertRaises(ValueError):
            main.extract_inspector_flag(['--inspect', '--inspect'])

    def test_empty_program(self):
        report = inspect_validated_program([])
        self.assertEqual(report.status, AnalysisStatus.PASS)
        self.assertEqual(report.reports, ())

    def test_function_report(self):
        program = [FunctionDefinition('int', 'answer', [], [ReturnStatement(Integer(42))])]
        report = inspect_validated_program(program)
        self.assertEqual(len(report.reports), 1)
        self.assertEqual(report.reports[0][0], 'answer')
        self.assertIn('Quar Inspector:', format_pipeline_inspection(report))

    def test_report_not_silent_about_unknown(self):
        program = [FunctionDefinition('int', 'answer', [], [ReturnStatement(Integer(42))])]
        report = inspect_validated_program(program)
        self.assertIn(report.status.value, format_pipeline_inspection(report))


if __name__ == '__main__':
    unittest.main()
