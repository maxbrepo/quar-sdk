"""Direct QIR unsigned ABI transport tests (not source-language SDL3 tests)."""
import unittest

from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QModule, QReturn, QType, QValue
from frontend.quar.qir.validation import QIRValidationError, validate_module
from qrvm.qir_program_backend import compile_qir_program
from qrvm.instructions import OpCode


class NativeU32QIRTests(unittest.TestCase):
    def module(self, value=0xFFFFFFFF, argument_type="u32", declared_type="u32"):
        argument = QValue("flag", QType(argument_type))
        result = QValue("returned", QType("u32"))
        block = QBlock("entry", (
            QInstruction("const", (), argument, value),
            QInstruction("native_call", (argument,), result, "native_echo"),
        ), QReturn())
        return QModule("u32_native", (QFunction("__qir_entry", QType("void"), (), (block,)),),
                       (("native_echo", (declared_type,), "u32"),))

    def test_u32_maximum_compiles(self):
        package = compile_qir_program(self.module())
        self.assertIn((OpCode.PUSH_INT, 0xFFFFFFFF), package["instructions"])
        self.assertIn((OpCode.CALL, ("native_echo", 1)), package["instructions"])

    def test_zero_compiles(self):
        validate_module(self.module(0))

    def test_negative_rejected(self):
        with self.assertRaises(QIRValidationError):
            validate_module(self.module(-1))

    def test_overflow_rejected(self):
        with self.assertRaises(QIRValidationError):
            validate_module(self.module(0x100000000))

    def test_signature_mismatch_rejected(self):
        with self.assertRaises(QIRValidationError):
            validate_module(self.module(7, declared_type="i32"))

    def test_bool_is_not_u32(self):
        with self.assertRaises(QIRValidationError):
            validate_module(self.module(True))


if __name__ == "__main__":
    unittest.main()
