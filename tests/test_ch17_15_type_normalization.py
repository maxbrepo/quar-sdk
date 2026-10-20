"""Regression coverage for the opt-in IR type normalization boundary."""
import unittest

from frontend.quar.ir.model import IRFunctionDefinition, IRLiteral, IRReturn, IRReference
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from frontend.quar.qir.type_normalization import (
    QIRTypeNormalizationError, normalize_ir_type,
)
from frontend.quar.qir.types import canonical_type
from frontend.quar.qir.validation import validate_function


class TypeNormalizationTests(unittest.TestCase):
    def test_all_builtin_numeric_aliases(self):
        from frontend.quar.numeric_types import TYPE_ALIASES
        for alias, expected in TYPE_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertEqual(normalize_ir_type(alias).name, expected)

    def test_canonical_type_unchanged(self):
        self.assertEqual(normalize_ir_type("i32"), canonical_type("i32"))

    def test_qir_still_rejects_alias(self):
        with self.assertRaises(ValueError):
            canonical_type("int")

    def test_custom_alias_chain(self):
        self.assertEqual(normalize_ir_type("Count", {"Count": "Index", "Index": "uint"}).name, "u32")

    def test_alias_cycle_rejected(self):
        with self.assertRaises(QIRTypeNormalizationError):
            normalize_ir_type("A", {"A": "B", "B": "A"})

    def test_builtin_shadowing_rejected(self):
        with self.assertRaises(QIRTypeNormalizationError):
            normalize_ir_type("int", {"int": "i64"})

    def test_unknown_type_rejected(self):
        with self.assertRaises(QIRTypeNormalizationError):
            normalize_ir_type("SomeClass")

    def test_invalid_alias_target_rejected(self):
        with self.assertRaises(QIRTypeNormalizationError):
            normalize_ir_type("Alias", {"Alias": "Missing"})

    def test_bridge_builtin_aliases(self):
        f = IRFunctionDefinition("f", "int", (("x", "int", None),), (IRReturn(IRReference("x")),))
        q = lower_ir_function(f)
        self.assertEqual(q.return_type.name, "i32")
        validate_function(q)

    def test_bridge_custom_alias(self):
        f = IRFunctionDefinition("f", "Counter", (("x", "Counter", None),), (IRReturn(IRReference("x")),))
        q = lower_ir_function(f, type_aliases={"Counter": "long"})
        self.assertEqual(q.return_type.name, "i64")
        validate_function(q)

    def test_bridge_custom_alias_requires_explicit_mapping(self):
        f = IRFunctionDefinition("f", "Counter", (), (IRReturn(IRLiteral(1)),))
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(f)

    def test_bridge_rejects_float_alias_in_integer_only_mode(self):
        f = IRFunctionDefinition("f", "float", (), (IRReturn(IRLiteral(1)),))
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(f)


if __name__ == "__main__":
    unittest.main()
