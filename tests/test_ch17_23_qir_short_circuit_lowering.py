"""Direct AST short-circuit lowering and executable C adapter checks."""
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import BinaryOperation, Boolean, FunctionDefinition, FunctionParameter, ReturnStatement, Variable
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.validation import validate_function


class ShortCircuitLoweringTests(unittest.TestCase):
    def lower(self, expression):
        function = FunctionDefinition("bool", "logical_test", [
            FunctionParameter("bool", "a"), FunctionParameter("bool", "b"),
            FunctionParameter("bool", "c")], [ReturnStatement(expression)])
        return lower_ast_function(function)

    def test_and_or_nested_validate(self):
        for expression in (
            BinaryOperation(Variable("a"), "and", Variable("b")),
            BinaryOperation(Variable("a"), "or", Variable("b")),
            BinaryOperation(Variable("a"), "and", BinaryOperation(Variable("b"), "or", Variable("c"))),
            BinaryOperation(BinaryOperation(Variable("a"), "or", Variable("b")), "and", Variable("c")),
        ):
            with self.subTest(expression=expression):
                function = self.lower(expression)
                validate_function(function)
                self.assertGreater(len(function.blocks), 1)

    @unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
    def test_nested_executable(self):
        function = self.lower(BinaryOperation(Variable("a"), "and", BinaryOperation(Variable("b"), "or", Variable("c"))))
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "program.c")
            library = os.path.join(directory, "program.so")
            with open(source, "w", encoding="utf-8") as output:
                output.write(emit_c_function(function))
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", source, "-o", library],
                           check=True, capture_output=True)
            call = ctypes.CDLL(library).logical_test
            call.argtypes = [ctypes.c_bool] * 3
            call.restype = ctypes.c_bool
            for a in (False, True):
                for b in (False, True):
                    for c in (False, True):
                        self.assertEqual(call(a, b, c), a and (b or c))

    def test_non_boolean_rejected(self):
        with self.assertRaises(QIRASTLoweringError):
            self.lower(BinaryOperation(Variable("a"), "and", 1))


if __name__ == "__main__":
    unittest.main()
