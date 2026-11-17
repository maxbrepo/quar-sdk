"""Check frontend-neutral payload typing before implementing runtime enum storage."""
import unittest

from frontend.quar.ast_nodes import EnumDefinition, EnumVariant
from frontend.quar.ir.model import IREnumDefinition, IREnumVariant
from frontend.quar.qir.enum_layout import QIREnumLayoutError, lower_enum_layout
from frontend.quar.qir.enum_payload import payload_contract
from frontend.quar.qir.model import QType


class EnumPayloadContractTests(unittest.TestCase):
    def setUp(self):
        self.ast = EnumDefinition("Result", [
            EnumVariant("Ok", ["i32", "bool"]),
            EnumVariant("Error", ["i32"]),
            EnumVariant("Empty", []),
        ])

    def test_payload_types_and_tags(self):
        layout = lower_enum_layout(self.ast)
        contract = payload_contract(layout, "Ok")
        self.assertEqual(contract.tag, 0)
        self.assertEqual(contract.types, (QType("i32"), QType("bool")))
        self.assertEqual(contract.bind(("value", "ready")),
                         (("value", QType("i32")), ("ready", QType("bool"))))
        contract.validate_arguments((QType("i32"), QType("bool")))

    def test_invalid_construction_rejected(self):
        contract = payload_contract(lower_enum_layout(self.ast), "Ok")
        for arguments in ((QType("i32"),), (QType("bool"), QType("i32"))):
            with self.subTest(arguments=arguments), self.assertRaises(QIREnumLayoutError):
                contract.validate_arguments(arguments)

    def test_invalid_bindings_rejected(self):
        contract = payload_contract(lower_enum_layout(self.ast), "Ok")
        for names in (("x",), ("x", "x"), ("", "y")):
            with self.subTest(names=names), self.assertRaises(QIREnumLayoutError):
                contract.bind(names)

    def test_payload_free_variant_and_unknown_variant(self):
        layout = lower_enum_layout(self.ast)
        empty = payload_contract(layout, "Empty")
        self.assertEqual(empty.bind(()), ())
        empty.validate_arguments(())
        with self.assertRaises(QIREnumLayoutError):
            payload_contract(layout, "Missing")

    def test_ast_and_ir_contracts_match(self):
        ir = IREnumDefinition("Result", (
            IREnumVariant("Ok", ("i32", "bool")),
            IREnumVariant("Error", ("i32",)),
            IREnumVariant("Empty", ()),
        ))
        self.assertEqual(payload_contract(lower_enum_layout(self.ast), "Ok"),
                         payload_contract(lower_enum_layout(ir), "Ok"))


if __name__ == "__main__":
    unittest.main()
