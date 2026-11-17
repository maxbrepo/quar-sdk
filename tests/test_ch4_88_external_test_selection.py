"""Ensure selected external tests can import their sibling test helpers."""
import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from main import run_external_test_selection


class ExternalTestSelectionTests(unittest.TestCase):
    def test_selected_test_can_import_sibling_helper(self):
        tests_root = Path(__file__).resolve().parent
        selected = [tests_root / "test_ch17_87_qir_loop_early_returns.py"]
        with patch("builtins.input", return_value=""), contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(run_external_test_selection(selected))

    def test_selected_recovery_test_can_import_sibling_helper(self):
        tests_root = Path(__file__).resolve().parent
        selected = [tests_root / "test_ch17_56_qir_for_continue_recovery.py"]
        with patch("builtins.input", return_value=""), contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(run_external_test_selection(selected))


if __name__ == "__main__":
    unittest.main()
