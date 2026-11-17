"""QIR-06 candidate: symbolic/textual logic and lazy boolean branches."""
from __future__ import annotations

import unittest

from main import build_frontend
from frontend.quar.qir.program_lowering import lower_ast_program
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import execute


class QIR06LogicTests(unittest.TestCase):
    def run_source(self, condition: str) -> tuple[str, object]:
        source = ("i32 x = 1; if (" + condition + ") { print(7); } "
                  "else { print(8); }")
        ast, _ = build_frontend(source)
        module = lower_ast_program(ast)
        return execute(compile_qir_program(module)), module

    def test_symbolic_and_textual_forms_are_equivalent(self):
        for symbolic, textual, expected in (
            ("x == 1 && x != 2", "x == 1 and x != 2", "7\n"),
            ("x == 2 || x == 1", "x == 2 or x == 1", "7\n"),
            ("!(x == 1)", "not (x == 1)", "8\n"),
            ("x == 2 || x == 3", "x == 2 or x == 3", "8\n"),
        ):
            with self.subTest(symbolic=symbolic):
                self.assertEqual(self.run_source(symbolic)[0], expected)
                self.assertEqual(self.run_source(textual)[0], expected)

    def test_precedence_and_nested_boolean_branches(self):
        self.assertEqual(self.run_source("x == 1 || x == 2 && x == 3")[0], "7\n")
        self.assertEqual(self.run_source("(x == 1 || x == 2) && x == 3")[0], "8\n")
        self.assertEqual(self.run_source("!(x == 2 || x == 3) && x == 1")[0], "7\n")

    def test_short_circuit_is_encoded_as_control_flow(self):
        _, module = self.run_source("false && x == 1")
        blocks = module.functions[0].blocks
        self.assertTrue(any(block.phis for block in blocks))
        self.assertTrue(any(block.label.startswith("logical_rhs") for block in blocks))
        self.assertEqual(self.run_source("false && x == 1")[0], "8\n")
        self.assertEqual(self.run_source("true || x == 2")[0], "7\n")

    def test_mixed_syntax(self):
        self.assertEqual(self.run_source("!false && (x == 1 or x == 3)")[0], "7\n")


if __name__ == "__main__":
    unittest.main()
