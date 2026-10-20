"""Tests for the non-invasive QVM bytecode envelope."""
import unittest
from qrvm.bytecode_format import (BytecodeHeader, BytecodeFormatError,
    validate_bytecode_package, wrap_legacy_program)
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class BytecodeFormatTests(unittest.TestCase):
    def test_legacy_sequence(self):
        package = wrap_legacy_program([(OpCode.PUSH_INT, 7), (OpCode.HALT, None)])
        self.assertEqual(package["header"], BytecodeHeader())
        vm = QRVM()
        vm.run(package)
        self.assertEqual(vm.stack, [7])

    def test_legacy_mapping_is_unchanged(self):
        original = {"instructions": [(OpCode.HALT, None)], "functions": {}}
        package = wrap_legacy_program(original)
        self.assertNotIn("header", original)
        validate_bytecode_package(package)

    def test_function_package(self):
        package = wrap_legacy_program({"instructions": [(OpCode.HALT, None)],
            "functions": {"f": {"parameters": [], "return_type": "void",
                "instructions": [(OpCode.RETURN, None)]}}})
        validate_bytecode_package(package)

    def test_reject_wrong_magic(self):
        package = wrap_legacy_program([(OpCode.HALT, None)])
        package["header"] = BytecodeHeader(magic="BAD")
        with self.assertRaises(BytecodeFormatError):
            validate_bytecode_package(package)

    def test_reject_unsupported_major(self):
        package = wrap_legacy_program([(OpCode.HALT, None)])
        package["header"] = BytecodeHeader(major=2)
        with self.assertRaises(BytecodeFormatError):
            validate_bytecode_package(package)

    def test_reject_invalid_opcode(self):
        with self.assertRaises(BytecodeFormatError):
            wrap_legacy_program([("HALT", None)])

    def test_reject_malformed_instruction(self):
        with self.assertRaises(BytecodeFormatError):
            wrap_legacy_program([(OpCode.HALT,)])

    def test_reject_bad_function(self):
        with self.assertRaises(BytecodeFormatError):
            wrap_legacy_program({"instructions": [], "functions": {"f": {"instructions": []}}})

    def test_reject_double_wrap(self):
        with self.assertRaises(BytecodeFormatError):
            wrap_legacy_program(wrap_legacy_program([(OpCode.HALT, None)]))

    def test_reject_future_minor(self):
        package = wrap_legacy_program([(OpCode.HALT, None)])
        package["header"] = BytecodeHeader(minor=1)
        with self.assertRaises(BytecodeFormatError):
            validate_bytecode_package(package)
