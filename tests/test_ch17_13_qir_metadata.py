"""Metadata validation and preservation across QIR optimizations."""
import unittest
from dataclasses import replace
from frontend.quar.qir.model import (QType, QValue, QInstruction, QReturn, QBlock,
                                     QFunction, QMetadata, QSourceLocation, QSafetyMetadata)
from frontend.quar.qir.validation import validate_function, QIRValidationError
from frontend.quar.qir.global_constants import propagate_integer_constants

class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.i32 = QType("i32")
        self.x = QValue("x", self.i32)
        self.meta = QMetadata(QSourceLocation("example.quar", 4, 7),
                              QSafetyMetadata(("overflow",), ("inspector:arith",)))

    def function(self, metadata):
        instruction = QInstruction("const", (), self.x, 12, metadata)
        return QFunction("main", self.i32, (),
                         (QBlock("entry", (instruction,), QReturn(self.x)),))

    def test_valid_metadata(self):
        validate_function(self.function(self.meta))

    def test_metadata_optional(self):
        validate_function(self.function(None))

    def test_invalid_line(self):
        with self.assertRaises(QIRValidationError):
            validate_function(self.function(replace(self.meta, source=QSourceLocation("a", 0, 1))))

    def test_invalid_column(self):
        with self.assertRaises(QIRValidationError):
            validate_function(self.function(replace(self.meta, source=QSourceLocation("a", 1, -1))))

    def test_unknown_check(self):
        with self.assertRaises(QIRValidationError):
            validate_function(self.function(replace(self.meta, safety=QSafetyMetadata(("magic",)))))

    def test_duplicate_check(self):
        with self.assertRaises(QIRValidationError):
            validate_function(self.function(replace(self.meta, safety=QSafetyMetadata(("null", "null")))))

    def test_invalid_tag(self):
        with self.assertRaises(QIRValidationError):
            validate_function(self.function(replace(self.meta, safety=QSafetyMetadata((), ("",)))))

    def test_global_constant_folding_preserves_metadata(self):
        y = QValue("y", self.i32)
        instruction = QInstruction("copy", (self.x,), y, metadata=self.meta)
        function = QFunction("main", self.i32, (), (QBlock("entry", (
            QInstruction("const", (), self.x, 12), instruction), QReturn(y)),))
        optimized = propagate_integer_constants(function)
        self.assertEqual(optimized.blocks[0].instructions[1].metadata, self.meta)
        validate_function(optimized)

    def test_immutable_metadata(self):
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            self.meta.source = None

if __name__ == "__main__":
    unittest.main()
