"""Chapter 17.10: conservative integer constant folding tests."""
import unittest
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QReturn, QType, QValue
from frontend.quar.qir.constant_folding import fold_integer_constants
from frontend.quar.qir.validation import QIRValidationError, validate_function

def value(name, typ="i32"):
    return QValue(name, QType(typ))

def function(instructions, result="out", typ="i32"):
    return QFunction("f", QType(typ), (), (QBlock("entry", tuple(instructions), QReturn(value(result, typ))),))

class TestConstantFolding(unittest.TestCase):
    def test_add(self):
        f = function((QInstruction("const", (), value("a"), 12), QInstruction("const", (), value("b"), 30), QInstruction("add", (value("a"), value("b")), value("out"))))
        folded = fold_integer_constants(f)
        self.assertEqual(folded.blocks[0].instructions[-1].immediate, 42)
        self.assertEqual(f.blocks[0].instructions[-1].opcode, "add")

    def test_sub_mul(self):
        f = function((QInstruction("const", (), value("a"), 10), QInstruction("const", (), value("b"), 3), QInstruction("sub", (value("a"), value("b")), value("c")), QInstruction("mul", (value("c"), value("b")), value("out"))))
        self.assertEqual(fold_integer_constants(f).blocks[0].instructions[-1].immediate, 21)

    def test_copy(self):
        f = function((QInstruction("const", (), value("a"), 7), QInstruction("copy", (value("a"),), value("out"))))
        self.assertEqual(fold_integer_constants(f).blocks[0].instructions[-1].immediate, 7)

    def test_overflow_is_not_folded(self):
        f = function((QInstruction("const", (), value("a", "u8"), 255), QInstruction("const", (), value("b", "u8"), 1), QInstruction("add", (value("a", "u8"), value("b", "u8")), value("out", "u8"))), typ="u8")
        self.assertEqual(fold_integer_constants(f).blocks[0].instructions[-1].opcode, "add")

    def test_division_is_not_folded(self):
        f = function((QInstruction("const", (), value("a"), 6), QInstruction("const", (), value("b"), 0), QInstruction("div", (value("a"), value("b")), value("out"))))
        self.assertEqual(fold_integer_constants(f).blocks[0].instructions[-1].opcode, "div")

    def test_nonconstant_is_not_folded(self):
        f = QFunction("f", QType("i32"), (value("x"),), (QBlock("entry", (QInstruction("const", (), value("a"), 1), QInstruction("add", (value("a"), value("x")), value("out"))), QReturn(value("out"))),))
        self.assertEqual(fold_integer_constants(f).blocks[0].instructions[-1].opcode, "add")

    def test_out_of_range_literal_rejected(self):
        f = function((QInstruction("const", (), value("out", "u8"), 256),), typ="u8")
        with self.assertRaises(QIRValidationError):
            validate_function(f)

    def test_boolean_literal_rejected(self):
        f = function((QInstruction("const", (), value("out"), True),))
        with self.assertRaises(QIRValidationError):
            validate_function(f)

    def test_idempotent(self):
        f = function((QInstruction("const", (), value("a"), 1), QInstruction("copy", (value("a"),), value("out"))))
        self.assertEqual(fold_integer_constants(fold_integer_constants(f)), fold_integer_constants(f))

if __name__ == "__main__":
    unittest.main()
