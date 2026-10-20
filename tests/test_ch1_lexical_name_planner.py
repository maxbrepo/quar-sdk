"""Contract for future backend-neutral lexical name lowering."""
import unittest

from frontend.quar.lexical_lowering import LexicalNamePlanner
from frontend.quar.scope_symbols import DuplicateBindingError


class LexicalNamePlannerTests(unittest.TestCase):
    def test_explicit_shadowing_restores_outer_storage(self):
        planner = LexicalNamePlanner()
        outer = planner.declare("count").storage_name
        planner.enter()
        inner = planner.declare("count").storage_name
        self.assertNotEqual(outer, inner)
        self.assertEqual(planner.read("count"), inner)
        planner.leave()
        self.assertEqual(planner.read("count"), outer)

    def test_assignment_targets_existing_outer_binding(self):
        planner = LexicalNamePlanner()
        outer = planner.declare("value").storage_name
        planner.enter()
        result = planner.assign("value", allow_inference=True)
        self.assertFalse(result.introduced)
        self.assertEqual(result.storage_name, outer)
        planner.leave()

    def test_inferred_name_is_local_to_its_scope(self):
        planner = LexicalNamePlanner()
        planner.enter()
        local = planner.assign("temporary", allow_inference=True)
        self.assertTrue(local.introduced)
        self.assertEqual(planner.read("temporary"), local.storage_name)
        planner.leave()
        with self.assertRaises(NameError):
            planner.read("temporary")

    def test_duplicate_and_unknown_names_are_rejected(self):
        planner = LexicalNamePlanner()
        planner.declare("x")
        with self.assertRaises(DuplicateBindingError):
            planner.declare("x")
        with self.assertRaises(NameError):
            planner.assign("missing")
