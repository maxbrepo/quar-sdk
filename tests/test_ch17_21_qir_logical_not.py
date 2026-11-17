"""Regression coverage for strictly typed QIR logical negation."""
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (Boolean, FunctionDefinition, FunctionParameter,
                                      Integer, ReturnStatement, UnaryOperation, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QReturn, QType, QValue
from frontend.quar.qir.operations import QIROperationError, validate_instruction


class LogicalNotTests(unittest.TestCase):
    def test_ast_ir_parity(self):
        for operand in (Boolean(True), Boolean(False), Variable("flag")):
            with self.subTest(operand=operand):
                ast = FunctionDefinition("bool", "negate", [FunctionParameter("bool", "flag")],
                                         [ReturnStatement(UnaryOperation("!", operand))])
                direct = lower_ast_function(ast)
                bridged = lower_ir_function(lower_statement(ast))
                self.assertEqual([(i.opcode, i.immediate) for i in direct.blocks[0].instructions],
                                 [(i.opcode, i.immediate) for i in bridged.blocks[0].instructions])
                self.assertEqual(direct.blocks[0].instructions[-1].opcode, "logical_not")

    def test_reject_integer_operand(self):
        ast = FunctionDefinition("bool", "negate", [], [ReturnStatement(UnaryOperation("!", Integer(1)))])
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(ast)
        x = QValue("x", QType("i32"))
        y = QValue("y", QType("bool"))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("logical_not", (x,), y))

    def test_boolean_constant_requires_bool(self):
        x = QValue("x", QType("i32"))
        with self.assertRaises(QIROperationError):
            validate_instruction(QInstruction("const", (), x, True))

    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_c_backend_boolean_negation(self):
        param = QValue("flag", QType("bool"))
        result = QValue("result", QType("bool"))
        fn = QFunction("negate", QType("bool"), (param,),
                       (QBlock("entry", (QInstruction("logical_not", (param,), result),), QReturn(result)),))
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "qir.c")
            library = os.path.join(directory, "qir.so")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(emit_c_function(fn))
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", source, "-o", library],
                           check=True, capture_output=True)
            method = ctypes.CDLL(library).negate
            method.argtypes = [ctypes.c_bool]
            method.restype = ctypes.c_bool
            self.assertFalse(method(True))
            self.assertTrue(method(False))
