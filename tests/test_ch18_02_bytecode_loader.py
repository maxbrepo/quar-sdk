"""Chapter 18.2: in-memory QVM loader integration tests."""
import unittest

from qrvm.bytecode_format import BytecodeHeader, wrap_legacy_program
from qrvm.bytecode_loader import (
    BytecodeLoadError,
    LoadedBytecode,
    load_bytecode,
    run_loaded_bytecode,
)
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class BytecodeLoaderTests(unittest.TestCase):
    def sample(self):
        return wrap_legacy_program([(OpCode.PUSH_INT, 19), (OpCode.HALT, None)])

    def test_load_versioned(self):
        loaded = load_bytecode(self.sample())
        self.assertEqual(loaded.header, BytecodeHeader())

    def test_execute_loaded(self):
        vm = QRVM()
        run_loaded_bytecode(vm, load_bytecode(self.sample()))
        self.assertEqual(vm.stack, [19])

    def test_legacy_rejected_by_default(self):
        with self.assertRaisesRegex(BytecodeLoadError, "allow_legacy"):
            load_bytecode([(OpCode.HALT, None)])

    def test_legacy_explicitly_accepted(self):
        loaded = load_bytecode([(OpCode.PUSH_INT, 4), (OpCode.HALT, None)], allow_legacy=True)
        vm = QRVM()
        run_loaded_bytecode(vm, loaded)
        self.assertEqual(vm.stack, [4])

    def test_invalid_major_rejected(self):
        package = self.sample()
        package["header"] = BytecodeHeader(major=9)
        with self.assertRaises(BytecodeLoadError):
            load_bytecode(package)

    def test_invalid_opcode_rejected(self):
        package = self.sample()
        package["instructions"] = [("PUSH_INT", 1)]
        with self.assertRaises(BytecodeLoadError):
            load_bytecode(package)

    def test_source_mutation_does_not_change_loaded_snapshot(self):
        package = self.sample()
        loaded = load_bytecode(package)
        package["instructions"][0] = (OpCode.PUSH_INT, 99)
        vm = QRVM()
        run_loaded_bytecode(vm, loaded)
        self.assertEqual(vm.stack, [19])

    def test_loaded_mutation_is_revalidated(self):
        loaded = load_bytecode(self.sample())
        loaded.package["instructions"][0] = ("INVALID", None)
        with self.assertRaises(BytecodeLoadError):
            run_loaded_bytecode(QRVM(), loaded)

    def test_header_mismatch_rejected(self):
        loaded = load_bytecode(self.sample())
        loaded.package["header"] = BytecodeHeader(minor=0, major=2)
        with self.assertRaises(BytecodeLoadError):
            run_loaded_bytecode(QRVM(), loaded)

    def test_wrong_loaded_object_rejected(self):
        with self.assertRaises(BytecodeLoadError):
            run_loaded_bytecode(QRVM(), self.sample())

    def test_existing_function_table_preserved(self):
        package = wrap_legacy_program({"instructions": [(OpCode.HALT, None)],
            "functions": {"f": {"parameters": [], "return_type": "void",
                "instructions": [(OpCode.RETURN, None)]}}})
        loaded = load_bytecode(package)
        self.assertIn("f", loaded.package["functions"])

    def test_loaded_object_can_be_reloaded(self):
        first = load_bytecode(self.sample())
        second = load_bytecode(first)
        self.assertIsNot(first.package, second.package)
        self.assertEqual(first.package, second.package)
