"""Validate deterministic enum layout shared by AST and legacy IR."""
import unittest

from frontend.quar.ast_nodes import EnumDefinition, EnumVariant
from frontend.quar.ir.model import IREnumDefinition, IREnumVariant
from frontend.quar.qir.enum_layout import QIREnumLayoutError, lower_enum_layout


class QIREnumLayoutTests(unittest.TestCase):
    def test_ast_and_legacy_ir_have_identical_layout(self):
        ast = EnumDefinition("Option", [EnumVariant("None", []), EnumVariant("Some", ["i32"])])
        ir = IREnumDefinition("Option", (IREnumVariant("None", ()), IREnumVariant("Some", ("i32",))))
        self.assertEqual(lower_enum_layout(ast), lower_enum_layout(ir))
        self.assertEqual(lower_enum_layout(ast).variant("Some").tag, 1)
        self.assertEqual(lower_enum_layout(ast).variant("Some").payload_types, ("i32",))

    def test_declaration_order_is_canonical(self):
        layout = lower_enum_layout(EnumDefinition("State", [EnumVariant("Pending", []), EnumVariant("Done", [])]))
        self.assertEqual(tuple(v.tag for v in layout.variants), (0, 1))
        with self.assertRaisesRegex(QIREnumLayoutError, "Unknown variant"):
            layout.variant("Missing")

    def test_rejects_duplicate_variants(self):
        with self.assertRaisesRegex(QIREnumLayoutError, "Duplicate"):
            lower_enum_layout(EnumDefinition("Bad", [EnumVariant("A", []), EnumVariant("A", [])]))

    def test_rejects_invalid_declarations(self):
        for definition in (EnumDefinition("Empty", []), EnumDefinition("Bad", [EnumVariant("A", [""])])):
            with self.subTest(definition=definition), self.assertRaises(QIREnumLayoutError):
                lower_enum_layout(definition)


if __name__ == "__main__":
    unittest.main()
