"""Chapter 15.23: reusable conservative dataflow lattice."""
import unittest
from qrvm.optional_flow import FlowState, Presence
from qrvm.compiler import QRVMCompiler
from frontend.quar.ast_nodes import (VariableDeclaration, Assignment, Integer,
                                      Boolean, IfStatement, Variable, FunctionCall)


class OptionalFlowTests(unittest.TestCase):
    def test_missing_is_unknown(self):
        self.assertIs(FlowState().get("x"), Presence.UNKNOWN)

    def test_states_are_immutable(self):
        initial = FlowState()
        updated = initial.set("x", Presence.PRESENT)
        self.assertIs(initial.get("x"), Presence.UNKNOWN)
        self.assertIs(updated.get("x"), Presence.PRESENT)

    def test_join_preserves_agreement(self):
        a = FlowState().set("x", Presence.PRESENT)
        self.assertIs(a.join(a).get("x"), Presence.PRESENT)

    def test_join_discards_disagreement(self):
        a = FlowState().set("x", Presence.PRESENT)
        b = FlowState().set("x", Presence.ABSENT)
        self.assertIs(a.join(b).get("x"), Presence.UNKNOWN)
        self.assertEqual(a.join(b), b.join(a))

    def test_join_with_unknown_discards_fact(self):
        a = FlowState().set("x", Presence.PRESENT)
        self.assertIs(a.join(FlowState()).get("x"), Presence.UNKNOWN)

    def test_invalidation_does_not_remove_other_facts(self):
        state = FlowState().refine({"x": Presence.PRESENT, "y": Presence.ABSENT})
        updated = state.invalidate({"x"})
        self.assertIs(updated.get("x"), Presence.UNKNOWN)
        self.assertIs(updated.get("y"), Presence.ABSENT)

    def test_refinement_overrides_old_fact(self):
        state = FlowState().set("x", Presence.ABSENT)
        self.assertIs(state.refine({"x": Presence.PRESENT}).get("x"), Presence.PRESENT)

    def test_compiler_branch_join_retains_absence(self):
        compiler = QRVMCompiler()
        compiler.compile([
            VariableDeclaration("int?", "x", None),
            IfStatement(Boolean(True), [Assignment("x", None)], [Assignment("x", None)]),
        ])
        self.assertIs(compiler._optional_presence["x"], False)

    def test_compiler_branch_join_discards_disagreement(self):
        compiler = QRVMCompiler()
        compiler.compile([
            VariableDeclaration("int?", "x", None),
            IfStatement(Boolean(True), [Assignment("x", Integer(3))], [Assignment("x", None)]),
        ])
        self.assertIsNone(compiler._optional_presence["x"])


if __name__ == "__main__":
    unittest.main()
