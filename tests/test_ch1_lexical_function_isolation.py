"""Regression checks for lexical namespace isolation before compiler wiring."""
import unittest

from frontend.quar.scope_symbols import LexicalBindings


class LexicalFunctionIsolationTests(unittest.TestCase):
    def test_function_namespaces_are_isolated(self):
        bindings = LexicalBindings()
        outer = bindings.declare("value")
        with bindings.function_scoped():
            self.assertIsNone(bindings.resolve("value"))
            first = bindings.declare("value")
            self.assertNotEqual(first.internal_name, outer.internal_name)
        self.assertEqual(bindings.resolve_required("value"), outer)
        with bindings.function_scoped():
            second = bindings.declare("value")
            self.assertNotEqual(second.internal_name, first.internal_name)

    def test_exception_restores_original_namespace(self):
        bindings = LexicalBindings()
        original = bindings.declare("outer")
        with self.assertRaisesRegex(RuntimeError, "stop"):
            with bindings.function_scoped():
                bindings.declare("local")
                raise RuntimeError("stop")
        self.assertEqual(bindings.resolve_required("outer"), original)
        self.assertIsNone(bindings.resolve("local"))

    def test_visible_bindings_snapshot_and_shadowing(self):
        bindings = LexicalBindings()
        outer = bindings.declare("value")
        snapshot = bindings.visible_bindings()
        with bindings.scoped():
            inner = bindings.declare("value")
            self.assertEqual(bindings.visible_bindings()["value"], inner)
            self.assertEqual(snapshot["value"], outer)
        self.assertEqual(bindings.visible_bindings()["value"], outer)


if __name__ == "__main__":
    unittest.main()
