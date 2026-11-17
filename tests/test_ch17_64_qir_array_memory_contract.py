"""Validate the initial indexed-memory QIR contract (not executable yet)."""
import unittest

from frontend.quar.qir.model import QInstruction, QMetadata, QSafetyMetadata, QType, QValue
from frontend.quar.qir.operations import QIROperationError, validate_instruction


class ArrayMemoryContractTests(unittest.TestCase):
    def setUp(self):
        self.pointer = QValue("storage", QType("ptr<i32>"))
        self.index = QValue("index", QType("i32"))
        self.value = QValue("value", QType("i32"))
        self.bounds = QMetadata(safety=QSafetyMetadata(checks=("bounds",)))

    def test_allocation_has_explicit_positive_capacity(self):
        validate_instruction(QInstruction("array_alloc", (), self.pointer, 3))
        for size in (0, -1, 1_000_001, True):
            with self.subTest(size=size), self.assertRaises(QIROperationError):
                validate_instruction(QInstruction("array_alloc", (), self.pointer, size))

    def test_read_requires_bounds_obligation(self):
        validate_instruction(QInstruction("array_get", (self.pointer, self.index), self.value, metadata=self.bounds))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("array_get", (self.pointer, self.index), self.value))

    def test_write_requires_bounds_obligation(self):
        validate_instruction(QInstruction("array_set", (self.pointer, self.index, self.value), metadata=self.bounds))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("array_set", (self.pointer, self.index, self.value)))

    def test_wrong_index_type_is_rejected(self):
        wrong = QValue("wrong", QType("bool"))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("array_get", (self.pointer, wrong), self.value, metadata=self.bounds))

    def test_wrong_element_type_is_rejected(self):
        wrong = QValue("wrong", QType("i16"))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("array_set", (self.pointer, self.index, wrong), metadata=self.bounds))


if __name__ == "__main__":
    unittest.main()
