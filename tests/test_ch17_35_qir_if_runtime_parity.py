"""Executable parity tests for conditional QIR from both lowering routes."""
import ctypes
import itertools
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionDefinition,
                                     FunctionParameter, IfStatement, Integer, ReturnStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.validation import validate_function


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class ConditionalRuntimeParityTests(unittest.TestCase):
    def check_function(self, function, arguments, expected):
        for route, qir in (("direct", lower_ast_function(function)),
                           ("bridge", lower_ir_function(lower_statement(function)))):
            with self.subTest(route=route, function=function.name):
                validate_function(qir)
                with tempfile.TemporaryDirectory() as directory:
                    source = os.path.join(directory, "test.c")
                    library = os.path.join(directory, "test.so")
                    with open(source, "w", encoding="utf-8") as stream:
                        stream.write(emit_c_function(qir))
                    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
                                    "-shared", "-fPIC", source, "-o", library],
                                   check=True, capture_output=True, timeout=15)
                    entry = getattr(ctypes.CDLL(library), function.name)
                    entry.argtypes = [ctypes.c_bool] * (len(function.parameters) - 1) + [ctypes.c_int32]
                    entry.restype = ctypes.c_int32
                    for args, result in zip(arguments, expected):
                        self.assertEqual(entry(*args), result, f"{route}: {args}")

    def test_else_if_chain(self):
        # An else-if chain is represented as nested IfStatement nodes.
        function = FunctionDefinition("i32", "chain", [FunctionParameter("bool", "a"),
            FunctionParameter("bool", "b"), FunctionParameter("i32", "x")], [
            IfStatement(Variable("a"), [Assignment("x", Integer(10))], [
                IfStatement(Variable("b"), [Assignment("x", Integer(20))],
                            [Assignment("x", Integer(30))])]),
            ReturnStatement(Variable("x"))])
        args = list(itertools.product((False, True), (False, True), (-5, 7)))
        self.check_function(function, args, [10 if a else 20 if b else 30 for a, b, _ in args])

    def test_nested_and_short_circuit_condition(self):
        function = FunctionDefinition("i32", "nested_condition", [FunctionParameter("bool", "a"),
            FunctionParameter("bool", "b"), FunctionParameter("i32", "x")], [
            IfStatement(BinaryOperation(Variable("a"), "and", Variable("b")), [
                IfStatement(Variable("b"), [Assignment("x", Integer(11))],
                            [Assignment("x", Integer(12))])],
                [Assignment("x", Integer(13))]),
            ReturnStatement(Variable("x"))])
        args = list(itertools.product((False, True), (False, True), (-5, 7)))
        self.check_function(function, args, [11 if a and b else 13 for a, b, _ in args])

    def test_if_without_else_keeps_original_value(self):
        function = FunctionDefinition("i32", "optional_branch", [FunctionParameter("bool", "a"),
            FunctionParameter("bool", "b"), FunctionParameter("i32", "x")], [
            IfStatement(BinaryOperation(Variable("a"), "or", Variable("b")),
                        [Assignment("x", Integer(99))], []),
            ReturnStatement(Variable("x"))])
        args = list(itertools.product((False, True), (False, True), (-5, 7)))
        self.check_function(function, args, [99 if a or b else x for a, b, x in args])


if __name__ == "__main__":
    unittest.main()
