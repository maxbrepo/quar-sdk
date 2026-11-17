"""Validate the bootstrap tagged-value runtime without claiming a stable ABI."""
import unittest

from frontend.quar.ast_nodes import EnumDefinition, EnumVariant
from frontend.quar.ir.model import IREnumDefinition, IREnumVariant
from frontend.quar.qir.enum_layout import QIREnumLayoutError, lower_enum_layout
from frontend.quar.qir.enum_runtime import construct_enum_value


class EnumRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.layout = lower_enum_layout(EnumDefinition("Result", [
            EnumVariant("Ok", ["i32", "bool"]),
            EnumVariant("Error", ["i32"]),
            EnumVariant("Empty", []),
        ]))

    def test_construct_match_and_bind(self):
        value = construct_enum_value(self.layout, "Ok", (42, True))
        self.assertEqual(value.tag, 0)
        self.assertEqual(value.variant_name(), "Ok")
        self.assertTrue(value.matches("Ok"))
        self.assertFalse(value.matches("Error"))
        self.assertEqual(value.bindings("Ok", ("number", "ready")), {"number": 42, "ready": True})
        with self.assertRaises(QIREnumLayoutError):
            value.bindings("Error", ("error",))

    def test_empty_variant(self):
        value = construct_enum_value(self.layout, "Empty")
        self.assertEqual(value.bindings("Empty", ()), {})

    def test_reject_bad_payloads(self):
        for payload in ((True, True), (2**31, False), (-2**31 - 1, False),
                        (7, 1), (7,), (7, False, 8)):
            with self.subTest(payload=payload), self.assertRaises(QIREnumLayoutError):
                construct_enum_value(self.layout, "Ok", payload)
        with self.assertRaises(QIREnumLayoutError):
            construct_enum_value(self.layout, "Missing")

    def test_reject_unsupported_types(self):
        layout = lower_enum_layout(EnumDefinition("Other", [EnumVariant("Text", ["string"])]))
        with self.assertRaises(QIREnumLayoutError):
            construct_enum_value(layout, "Text", ("hello",))

    def test_ast_ir_runtime_parity(self):
        ir_layout = lower_enum_layout(IREnumDefinition("Result", (
            IREnumVariant("Ok", ("i32", "bool")),
            IREnumVariant("Error", ("i32",)),
            IREnumVariant("Empty", ()),
        )))
        self.assertEqual(construct_enum_value(self.layout, "Ok", (3, False)),
                         construct_enum_value(ir_layout, "Ok", (3, False)))


if __name__ == "__main__":
    unittest.main()
