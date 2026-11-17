"""QIR string operations are typed but not yet executable in the C adapter."""
import unittest

from frontend.quar.qir.model import (
    QBlock, QFunction, QInstruction, QMetadata, QReturn,
    QSafetyMetadata, QType, QValue,
)
from frontend.quar.qir.operations import QIROperationError, validate_instruction
from frontend.quar.qir.backend_readiness import inspect_backend_readiness


class StringOperationsContractTests(unittest.TestCase):
    def setUp(self):
        self.text = QValue("text", QType("string"))
        self.length = QValue("length", QType("i32"))
        self.checked = QMetadata(safety=QSafetyMetadata(checks=("string_length",)))

    def test_byte_length_contract(self):
        validate_instruction(QInstruction("string_byte_len", (self.text,), self.length, metadata=self.checked))

    def test_scalar_length_contract(self):
        validate_instruction(QInstruction("string_scalar_len", (self.text,), self.length, metadata=self.checked))

    def test_missing_runtime_safety_obligation_rejected(self):
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("string_scalar_len", (self.text,), self.length))

    def test_wrong_input_and_output_types_rejected(self):
        for operands, result in (
            ((QValue("n", QType("i32")),), self.length),
            ((self.text,), QValue("bad", QType("bool"))),
            ((), self.length),
        ):
            with self.subTest(operands=operands, result=result), self.assertRaises(QIROperationError):
                validate_instruction(QInstruction("string_byte_len", operands, result, metadata=self.checked))

    def test_c_backend_accepts_checked_length_operations(self):
        instruction = QInstruction("string_scalar_len", (self.text,), self.length, metadata=self.checked)
        function = QFunction("count_scalars", QType("i32"), (self.text,),
                             (QBlock("entry", (instruction,), QReturn(self.length)),))
        report = inspect_backend_readiness(function, "c")
        self.assertTrue(report.ready_for_adapter)
        self.assertFalse(inspect_backend_readiness(function, "qrvm").ready_for_adapter)


if __name__ == "__main__":
    unittest.main()
