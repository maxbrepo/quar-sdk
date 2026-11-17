"""Verify shared typed binding plans for AST and legacy IR match arms."""
import unittest

from frontend.quar.ast_nodes import EnumDefinition, EnumVariant, MatchArm
from frontend.quar.ir.model import IREnumDefinition, IREnumVariant, IRMatchArm
from frontend.quar.qir.enum_binding_plan import plan_match_bindings
from frontend.quar.qir.enum_layout import QIREnumLayoutError, lower_enum_layout
from frontend.quar.qir.model import QType


class EnumBindingPlanTests(unittest.TestCase):
    def setUp(self):
        self.ast_layout = lower_enum_layout(EnumDefinition("Result", [
            EnumVariant("Ok", ["i32", "bool"]), EnumVariant("Error", ["i32"]),
            EnumVariant("Empty", []),
        ]))
        self.ir_layout = lower_enum_layout(IREnumDefinition("Result", (
            IREnumVariant("Ok", ("i32", "bool")), IREnumVariant("Error", ("i32",)),
            IREnumVariant("Empty", ()),
        )))

    def test_ast_ir_binding_parity(self):
        ast = [MatchArm("Ok", ["number", "valid"], []), MatchArm("Empty", [], [])]
        ir = (IRMatchArm("Ok", ("number", "valid"), ()), IRMatchArm("Empty", (), ()))
        left = plan_match_bindings(self.ast_layout, ast)
        self.assertEqual(left, plan_match_bindings(self.ir_layout, ir))
        self.assertEqual(left[0].tag, 0)
        self.assertEqual(left[0].bindings[0].slot, "payload_0_0")
        self.assertEqual(left[0].bindings[1].type, QType("bool"))
        self.assertEqual(left[1].bindings, ())

    def test_reject_duplicate_or_unknown_variants(self):
        for arms in ([MatchArm("Ok", ["a", "b"], []), MatchArm("Ok", ["c", "d"], [])],
                     [MatchArm("Missing", [], [])]):
            with self.subTest(arms=arms), self.assertRaises(QIREnumLayoutError):
                plan_match_bindings(self.ast_layout, arms)

    def test_reject_bad_binding_arity_and_names(self):
        for names in (["only_one"], ["same", "same"], ["", "other"]):
            with self.subTest(names=names), self.assertRaises(QIREnumLayoutError):
                plan_match_bindings(self.ast_layout, [MatchArm("Ok", names, [])])

    def test_reject_invalid_input(self):
        with self.assertRaises(QIREnumLayoutError):
            plan_match_bindings(self.ast_layout, None)
        with self.assertRaises(QIREnumLayoutError):
            plan_match_bindings(self.ast_layout, [object()])


if __name__ == "__main__":
    unittest.main()
