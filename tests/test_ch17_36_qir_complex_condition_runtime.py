"""Runtime parity for nested logical and numeric conditional expressions."""
import ctypes
import itertools
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, FunctionDefinition,
                                     FunctionParameter, IfStatement, Integer,
                                     ReturnStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.validation import validate_function


def comparison(left, operator, right):
    """Build an integer comparison; returns its AST expression."""
    return BinaryOperation(left, operator, right)


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class ComplexConditionRuntimeTests(unittest.TestCase):
    def check_function(self, function, arguments, expected):
        """Compile both lowering routes and compare their runtime results."""
        for route, qir in (("direct", lower_ast_function(function)),
                           ("bridge", lower_ir_function(lower_statement(function)))):
            with self.subTest(route=route, function=function.name):
                validate_function(qir)
                with tempfile.TemporaryDirectory() as directory:
                    source = os.path.join(directory, "test.c")
                    library = os.path.join(directory, "test.so")
                    with open(source, "w", encoding="utf-8") as stream:
                        stream.write(emit_c_function(qir))
                    subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                                    "-Wno-unused-parameter", "-shared", "-fPIC",
                                    source, "-o", library], check=True,
                                   capture_output=True, timeout=15)
                    entry = getattr(ctypes.CDLL(library), function.name)
                    entry.argtypes = [ctypes.c_bool if p.var_type == "bool" else ctypes.c_int32
                                      for p in function.parameters]
                    entry.restype = ctypes.c_int32
                    for args, result in zip(arguments, expected):
                        self.assertEqual(entry(*args), result, f"{route}: {args}")

    def test_mixed_and_or_with_comparisons(self):
        condition = BinaryOperation(
            comparison(Variable("x"), ">", Integer(0)), "and",
            BinaryOperation(comparison(Variable("y"), "<", Integer(10)), "or",
                            comparison(Variable("x"), "==", Variable("y"))))
        function = FunctionDefinition("i32", "mixed_condition", [
            FunctionParameter("i32", "x"), FunctionParameter("i32", "y")], [
            IfStatement(condition, [Assignment("x", Integer(101))],
                        [Assignment("x", Integer(202))]),
            ReturnStatement(Variable("x"))])
        args = list(itertools.product((-5, 0, 3, 12), (-2, 3, 10, 12)))
        self.check_function(function, args, [101 if x > 0 and (y < 10 or x == y) else 202
                                             for x, y in args])

    def test_short_circuit_skips_division_by_zero_in_if(self):
        dangerous = comparison(BinaryOperation(Variable("x"), "/", Integer(0)),
                               "==", Integer(1))
        condition = BinaryOperation(comparison(Variable("x"), "<", Integer(0)),
                                    "and", dangerous)
        function = FunctionDefinition("i32", "skip_danger", [FunctionParameter("i32", "x")], [
            IfStatement(condition, [Assignment("x", Integer(100))],
                        [Assignment("x", Integer(200))]),
            ReturnStatement(Variable("x"))])
        self.check_function(function, [(0,), (1,), (7,)], [200, 200, 200])

    def test_nested_branches_merge_multiple_values(self):
        function = FunctionDefinition("i32", "merge_two", [
            FunctionParameter("bool", "a"), FunctionParameter("bool", "b"),
            FunctionParameter("i32", "x"), FunctionParameter("i32", "y")], [
            IfStatement(Variable("a"), [
                Assignment("x", Integer(3)),
                IfStatement(Variable("b"), [Assignment("y", Integer(7))],
                            [Assignment("y", Integer(11))])], [
                Assignment("x", Integer(5)), Assignment("y", Integer(13))]),
            ReturnStatement(BinaryOperation(Variable("x"), "+", Variable("y")))])
        args = list(itertools.product((False, True), (False, True), (0, 4), (0, 9)))
        self.check_function(function, args, [3 + (7 if b else 11) if a else 18
                                             for a, b, _, _ in args])
