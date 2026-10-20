"""Tests for the GTK-independent Quar Inspector editor transport."""
import json
import unittest
from frontend.quar import ast_nodes as ast
from qrvm.inspector_editor import editor_json, editor_record
from qrvm.inspector_pipeline import inspect_validated_program


class EditorBridgeTests(unittest.TestCase):
    def _report(self, *, path='example.vq', span=True):
        variable = ast.Variable('missing')
        if span:
            variable.start, variable.end = (3, 5), (3, 12)
        return inspect_validated_program([ast.ReturnStatement(variable)], path=path)

    def _missing(self, report):
        return next(item for item in editor_record(report)['diagnostics']
                    if item['code'] == 'QI-SYM-001')

    def test_zero_based_end_exclusive_range(self):
        item = self._missing(self._report())
        self.assertEqual(item['range'], {'start': {'line': 2, 'character': 4},
                                         'end': {'line': 2, 'character': 11}})

    def test_source_path_is_preserved(self):
        self.assertEqual(self._missing(self._report())['path'], 'example.vq')

    def test_missing_source_coordinates_are_not_fabricated(self):
        item = self._missing(self._report(span=False))
        self.assertIsNone(item['range'])
        self.assertIsNone(item['position'])

    def test_without_path_coordinates_are_unknown(self):
        item = self._missing(self._report(path=None))
        self.assertIsNone(item['path'])
        self.assertIsNone(item['range'])

    def test_report_and_pass_statuses_are_retained(self):
        result = editor_record(self._report())
        self.assertEqual(result['coordinate_system'], 'zero_based_end_exclusive')
        self.assertEqual(result['reports'][0]['scope'], '<module>')
        self.assertTrue(result['reports'][0]['passes'])
        self.assertFalse(result['blocking'])

    def test_json_round_trip_and_unicode(self):
        payload = editor_json(self._report(path='sorgenti/à.vq'))
        decoded = json.loads(payload)
        self.assertEqual(decoded['schema_version'], 1)
        self.assertEqual(next(item for item in decoded['diagnostics']
                              if item['code'] == 'QI-SYM-001')['path'], 'sorgenti/à.vq')


if __name__ == '__main__':
    unittest.main()
