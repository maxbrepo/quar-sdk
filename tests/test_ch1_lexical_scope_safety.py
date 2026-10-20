"""Exception safety and identity stability for lexical bindings."""
import unittest

from frontend.quar.scope_symbols import DuplicateBindingError, LexicalBindings


class LexicalScopeSafetyTests(unittest.TestCase):
    def test_exception_restores_outer_scope(self):
        symbols = LexicalBindings()
        outer = symbols.declare("value")
        with self.assertRaisesRegex(RuntimeError, "abort"):
            with symbols.scoped():
                symbols.declare("value")
                raise RuntimeError("abort")
        self.assertEqual(symbols.depth, 0)
        self.assertEqual(symbols.resolve("value"), outer)

    def test_nearest_visible_binding_and_current_scope_lookup(self):
        symbols = LexicalBindings()
        outer = symbols.declare("item")
        with symbols.scoped():
            self.assertIsNone(symbols.resolve_current("item"))
            self.assertEqual(symbols.resolve("item"), outer)
            inner = symbols.declare("item")
            self.assertEqual(symbols.resolve_current("item"), inner)
            self.assertEqual(symbols.resolve("item"), inner)
        self.assertEqual(symbols.resolve("item"), outer)

    def test_failed_declaration_does_not_consume_symbol_identity(self):
        symbols = LexicalBindings()
        first = symbols.declare("first")
        with self.assertRaises(DuplicateBindingError):
            symbols.declare("first")
        second = symbols.declare("second")
        self.assertEqual(first.internal_name, "__vq_binding_1")
        self.assertEqual(second.internal_name, "__vq_binding_2")

    def test_nested_contexts_unwind_after_error(self):
        symbols = LexicalBindings()
        with self.assertRaises(ValueError):
            with symbols.scoped():
                with symbols.scoped():
                    raise ValueError("stop")
        self.assertEqual(symbols.depth, 0)
        self.assertIsNone(symbols.resolve("missing"))
