"""Resolution invariants required before compiler-wide lexical lowering."""
import unittest

from frontend.quar.scope_symbols import LexicalBindings, DuplicateBindingError


class LexicalResolutionContractTests(unittest.TestCase):
    def test_shadowing_restores_outer_identity(self):
        symbols = LexicalBindings()
        outer = symbols.declare("value")
        with symbols.scoped():
            inner = symbols.declare("value")
            self.assertNotEqual(outer.internal_name, inner.internal_name)
            self.assertEqual(symbols.resolve_required("value"), inner)
            self.assertTrue(symbols.is_declared_here("value"))
        self.assertEqual(symbols.resolve_required("value"), outer)

    def test_assignment_resolution_does_not_declare(self):
        symbols = LexicalBindings()
        outer = symbols.declare("counter")
        with symbols.scoped():
            self.assertFalse(symbols.is_declared_here("counter"))
            self.assertEqual(symbols.resolve_required("counter"), outer)
            self.assertFalse(symbols.is_declared_here("counter"))

    def test_duplicate_local_and_unknown_reference(self):
        symbols = LexicalBindings()
        symbols.declare("name")
        with self.assertRaises(DuplicateBindingError):
            symbols.declare("name")
        with self.assertRaisesRegex(NameError, "not declared"):
            symbols.resolve_required("missing")

    def test_sibling_scopes_do_not_share_identity(self):
        symbols = LexicalBindings()
        with symbols.scoped():
            left = symbols.declare("temporary")
        with symbols.scoped():
            right = symbols.declare("temporary")
        self.assertNotEqual(left.internal_name, right.internal_name)
        self.assertIsNone(symbols.resolve("temporary"))


if __name__ == "__main__":
    unittest.main()
