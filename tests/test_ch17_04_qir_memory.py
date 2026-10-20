"""Chapter 17.4: typed memory and explicit numeric casts."""
import unittest
from frontend.quar.qir.model import QType, QValue, QInstruction, QReturn, QBlock, QFunction
from frontend.quar.qir.types import canonical_type, pointer_type, pointee_type
from frontend.quar.qir.operations import QIROperationError, validate_instruction
from frontend.quar.qir.validation import validate_function, QIRValidationError

I32 = canonical_type("i32")
F64 = canonical_type("f64")
PTR = pointer_type(I32)

class TestQIRMemory(unittest.TestCase):
    def test_pointer_roundtrip(self):
        self.assertEqual(pointee_type(PTR), I32)

    def test_pointer_void_rejected(self):
        with self.assertRaises(ValueError):
            pointer_type(canonical_type("void"))

    def test_nested_pointer_rejected(self):
        with self.assertRaises(ValueError):
            pointer_type(PTR)

    def test_alloca(self):
        validate_instruction(QInstruction("alloca", result=QValue("slot", PTR)))

    def test_load(self):
        validate_instruction(QInstruction("load", (QValue("slot", PTR),), QValue("v", I32)))

    def test_store(self):
        validate_instruction(QInstruction("store", (QValue("slot", PTR), QValue("v", I32))))

    def test_store_mismatch(self):
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("store", (QValue("slot", PTR), QValue("v", F64))))

    def test_load_mismatch(self):
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("load", (QValue("slot", PTR),), QValue("v", F64)))

    def test_numeric_cast(self):
        validate_instruction(QInstruction("cast", (QValue("x", I32),), QValue("y", F64)))

    def test_pointer_cast_rejected(self):
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("cast", (QValue("x", PTR),), QValue("y", I32)))

    def test_function_integration(self):
        instructions = (
            QInstruction("alloca", result=QValue("slot", PTR)),
            QInstruction("store", (QValue("slot", PTR), QValue("x", I32))),
            QInstruction("load", (QValue("slot", PTR),), QValue("y", I32)),
        )
        validate_function(QFunction("f", I32, (QValue("x", I32),),
                                    (QBlock("entry", instructions, QReturn(QValue("y", I32))),)))

    def test_function_rejects_bad_store(self):
        instruction = QInstruction("store", (QValue("slot", PTR), QValue("x", F64)))
        with self.assertRaises(QIRValidationError):
            validate_function(QFunction("f", QType("void"), (),
                                        (QBlock("entry", (instruction,), QReturn()),)))
