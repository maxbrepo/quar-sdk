"""Verify opt-in while-body lexical isolation in the real source pipeline."""
import contextlib
import io
import unittest

from main import build_frontend, run_qrvm


class WhileShadowingPipelineTests(unittest.TestCase):
    def test_while_body_can_shadow_outer_binding(self):
        source = "int value = 1; while (false) { int value = 2; print(value); } print(value);"
        program, types = build_frontend(source, lexical=True)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            run_qrvm(program, lexical=True)
        self.assertIn("=== QRVM OUTPUT ===\n1\n", captured.getvalue())

    def test_default_mode_still_rejects_while_shadowing(self):
        source = "int value = 1; while (false) { int value = 2; }"
        with self.assertRaises(Exception):
            build_frontend(source)
        build_frontend(source, lexical=True)

    def test_while_body_binding_not_visible_after_loop(self):
        source = "while (false) { int temporary = 2; } print(temporary);"
        with self.assertRaises(Exception):
            build_frontend(source, lexical=True)


if __name__ == "__main__":
    unittest.main()
