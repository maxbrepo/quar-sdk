"""Regression tests for Quar Inspector editor protocol validation."""
import copy
import json
import unittest

from frontend.quar import ast_nodes as ast
from qrvm.inspector_editor import editor_record, editor_json
from qrvm.inspector_editor_protocol import parse_editor_json, validate_editor_record
from qrvm.inspector_pipeline import inspect_validated_program


class EditorProtocolTests(unittest.TestCase):
    def setUp(self):
        variable = ast.Variable("missing")
        variable.start, variable.end = (4, 3), (4, 10)
        inspection = inspect_validated_program([ast.ReturnStatement(variable)], path="café/α.vq")
        self.payload = editor_record(inspection)

    def test_valid_payload_round_trip_preserves_unicode(self):
        self.assertEqual(parse_editor_json(json.dumps(self.payload, ensure_ascii=False)), self.payload)

    def test_current_editor_json_is_accepted(self):
        variable = ast.Variable("missing")
        inspection = inspect_validated_program([ast.ReturnStatement(variable)])
        self.assertEqual(parse_editor_json(editor_json(inspection))["schema_version"], 1)

    def test_future_schema_is_rejected(self):
        self.payload["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "schema version"):
            validate_editor_record(self.payload)

    def test_unknown_coordinate_system_is_rejected(self):
        self.payload["coordinate_system"] = "one_based"
        with self.assertRaisesRegex(ValueError, "coordinate system"):
            validate_editor_record(self.payload)

    def test_invalid_status_is_rejected(self):
        self.payload["reports"][0]["passes"][0]["status"] = "MAYBE"
        with self.assertRaisesRegex(ValueError, "invalid pass"):
            validate_editor_record(self.payload)

    def test_missing_coordinates_are_allowed(self):
        finding = self.payload["diagnostics"][0]
        finding["path"] = None
        finding["position"] = None
        finding["range"] = None
        self.assertIs(validate_editor_record(self.payload), self.payload)

    def test_negative_coordinate_is_rejected(self):
        finding = next(d for d in self.payload["diagnostics"] if d["range"])
        finding["range"]["end"]["character"] = -1
        with self.assertRaisesRegex(ValueError, "nonnegative integer"):
            validate_editor_record(self.payload)

    def test_inverted_range_is_rejected(self):
        finding = next(d for d in self.payload["diagnostics"] if d["range"])
        finding["range"]["end"] = copy.deepcopy(finding["range"]["start"])
        with self.assertRaisesRegex(ValueError, "end-exclusive"):
            validate_editor_record(self.payload)

    def test_position_must_match_range_start(self):
        finding = next(d for d in self.payload["diagnostics"] if d["range"])
        finding["position"]["character"] += 1
        with self.assertRaisesRegex(ValueError, "range start"):
            validate_editor_record(self.payload)

    def test_invalid_json_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid editor JSON"):
            parse_editor_json("{")


if __name__ == "__main__":
    unittest.main()
