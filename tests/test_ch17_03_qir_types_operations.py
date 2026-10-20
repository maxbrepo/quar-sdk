"""Chapter 17.3: canonical types and strictly typed value instructions."""
import unittest
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QReturn, QType, QValue
from frontend.quar.qir.operations import QIROperationError, validate_instruction
from frontend.quar.qir.types import canonical_type, is_integer, is_numeric
from frontend.quar.qir.validation import QIRValidationError, validate_function


class TestQIRTypesOperations(unittest.TestCase):
    def setUp(self):
        self.a = QValue("a", canonical_type("i32"))
        self.b = QValue("b", canonical_type("i32"))
        self.out = QValue("out", canonical_type("i32"))

    def test_canonical_primitives(self):
        for name in ("void", "bool", "string", "char", "i8", "u128", "f64"):
            self.assertEqual(canonical_type(name), QType(name))

    def test_aliases_are_not_implicitly_canonical(self):
        for name in ("int", "float", "byte", "i7", "struct", ""):
            with self.assertRaises(ValueError):
                canonical_type(name)

    def test_numeric_categories(self):
        self.assertTrue(is_integer(canonical_type("u64")))
        self.assertTrue(is_numeric(canonical_type("f32")))
        self.assertFalse(is_numeric(canonical_type("bool")))

    def test_arithmetic(self):
        for op in ("add", "sub", "mul", "div"):
            validate_instruction(QInstruction(op, (self.a, self.b), self.out))

    def test_no_implicit_conversion(self):
        other = QValue("f", canonical_type("f32"))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("add", (self.a, other), self.out))

    def test_comparisons(self):
        flag = QValue("flag", canonical_type("bool"))
        validate_instruction(QInstruction("lt", (self.a, self.b), flag))
        validate_instruction(QInstruction("eq", (flag, flag), flag))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("lt", (flag, flag), flag))

    def test_unknown_opcode_rejected(self):
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("load", (self.a,), self.out))

    def test_function_instruction_validation(self):
        fn = QFunction("sum", self.out.type, (self.a, self.b), (
            QBlock("entry", (QInstruction("add", (self.a, self.b), self.out),), QReturn(self.out)),
        ))
        validate_function(fn)

    def test_function_rejects_bad_instruction(self):
        fn = QFunction("sum", self.out.type, (self.a,), (
            QBlock("entry", (QInstruction("add", (self.a,), self.out),), QReturn(self.out)),
        ))
        with self.assertRaises(QIRValidationError):
            validate_function(fn)

    def test_function_rejects_alias_return_type(self):
        fn = QFunction("bad", QType("int"), (), (QBlock("entry", (), QReturn()),))
        with self.assertRaises(QIRValidationError):
            validate_function(fn)


if __name__ == "__main__":
    unittest.main()
