"""Cycle A: explicit QIR native call contract and QRVM FFI reuse."""
from __future__ import annotations

import ctypes.util
import unittest

from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QModule, QReturn, QType, QValue
from frontend.quar.qir.validation import QIRValidationError, validate_module
from qrvm.qir_program_backend import compile_qir_program
from qrvm.vm import QRVM
from qrvm.native_ffi import NativeLibrary


def module_for(symbol="abs", abi=(("i32",), "i32"), opcode="native_call"):
    number = QValue("number", QType("i32"))
    output = QValue("output", QType("i32"))
    return QModule("native_smoke", (QFunction("__qir_entry", QType("void"), (),
        (QBlock("entry", (QInstruction("const", (), number, -9),
                          QInstruction(opcode, (number,), output, symbol),
                          QInstruction("print", (output,))), QReturn()),)),),
        ((symbol, abi[0], abi[1]),))


class NativeQIRCycleATests(unittest.TestCase):
    def test_native_signature_exported_to_qrvm_package(self):
        package = compile_qir_program(module_for())
        self.assertEqual(package["native_declarations"], {"abs": (("i32",), "i32")})

    def test_reject_unknown_native_symbol(self):
        source = module_for()
        broken = QModule(source.name, source.functions, ())
        with self.assertRaisesRegex(QIRValidationError, "Native call ABI signature mismatch"):
            validate_module(broken)

    def test_reject_wrong_native_signature(self):
        with self.assertRaisesRegex(QIRValidationError, "Native call ABI signature mismatch"):
            validate_module(module_for(abi=(("bool",), "i32")))

    def test_reject_native_function_collision(self):
        source = module_for()
        with self.assertRaisesRegex(QIRValidationError, "Invalid or conflicting"):
            validate_module(QModule(source.name, source.functions,
                                    (("__qir_entry", ("i32",), "i32"),)))

    def test_native_call_reuses_existing_ffi(self):
        libc = ctypes.util.find_library("c")
        if not libc:
            self.skipTest("C runtime not found")
        package = compile_qir_program(module_for())
        vm = QRVM()
        vm.bind_native(package["native_declarations"], NativeLibrary(libc))
        vm.run(package)
        self.assertEqual(vm.stack, [])
