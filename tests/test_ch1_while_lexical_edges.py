"""Regression edges for experimental lexical while lowering in both backends."""
import unittest

from tests import test_ch1_c_while_lexical as while_parity
from main import build_frontend


class WhileLexicalEdgeTests(unittest.TestCase):
    check_source = while_parity.CWhileLexicalTests.check_source
    def test_zero_iteration_preserves_outer_binding(self):
        self.check_source(
            "int value = 4; while (false) { int value = 9; print(value); } print(value);",
            ["4"],
        )

    def test_nested_loops_restore_both_outer_bindings(self):
        self.check_source(
            "int outer = 0; int inner = 0; int value = 1; "
            "while (outer < 2) { "
            "int value = 2; inner = 0; "
            "while (inner < 2) { int value = 3; print(value); inner = inner + 1; } "
            "print(value); outer = outer + 1; } print(value);",
            ["3", "3", "2", "3", "3", "2", "1"],
        )

    def test_while_local_name_cannot_escape(self):
        with self.assertRaises(Exception):
            build_frontend("while (false) { int local = 1; } print(local);", lexical=True)
