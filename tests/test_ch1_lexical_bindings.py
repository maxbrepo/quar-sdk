"""Tests for the isolated lexical binding registry (not compiler integration)."""
import unittest
from frontend.quar.scope_symbols import DuplicateBindingError, LexicalBindings


class LexicalBindingTests(unittest.TestCase):
    def test_shadowing_restores_outer_binding(self):
        scopes = LexicalBindings()
        outer = scopes.declare("value")
        scopes.enter()
        inner = scopes.declare("value")
        self.assertNotEqual(outer.internal_name, inner.internal_name)
        self.assertEqual(scopes.resolve("value"), inner)
        scopes.leave()
        self.assertEqual(scopes.resolve("value"), outer)

    def test_duplicate_in_same_scope_is_rejected(self):
        scopes = LexicalBindings()
        scopes.declare("value")
        with self.assertRaises(DuplicateBindingError):
            scopes.declare("value")

    def test_sibling_scopes_use_distinct_internal_names(self):
        scopes = LexicalBindings()
        scopes.enter()
        first = scopes.declare("local")
        scopes.leave()
        self.assertIsNone(scopes.resolve("local"))
        scopes.enter()
        second = scopes.declare("local")
        self.assertNotEqual(first.internal_name, second.internal_name)
        scopes.leave()

    def test_root_scope_cannot_be_popped(self):
        with self.assertRaises(ValueError):
            LexicalBindings().leave()
