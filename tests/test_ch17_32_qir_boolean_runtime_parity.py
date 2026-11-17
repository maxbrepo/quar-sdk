"""Execute nested boolean QIR through both lowering routes and compare truth tables."""
import ctypes
import itertools
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import BinaryOperation, FunctionDefinition, FunctionParameter, ReturnStatement, Variable
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.validation import validate_function


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class BooleanRuntimeParityTests(unittest.TestCase):
    def test_nested_boolean_truth_tables(self):
        a, b, c = (Variable(name) for name in ("a", "b", "c"))
        cases = (
            (BinaryOperation(a, "and", BinaryOperation(b, "or", c)),
             lambda x, y, z: x and (y or z)),
            (BinaryOperation(BinaryOperation(a, "or", b), "and", c),
             lambda x, y, z: (x or y) and z),
            (BinaryOperation(BinaryOperation(a, "and", b), "or", c),
             lambda x, y, z: (x and y) or z),
            (BinaryOperation(a, "or", BinaryOperation(b, "and", c)),
             lambda x, y, z: x or (y and z)),
        )
        for index, (expression, expected) in enumerate(cases):
            function = FunctionDefinition("bool", f"boolean_case_{index}",
                [FunctionParameter("bool", name) for name in ("a", "b", "c")],
                [ReturnStatement(expression)])
            routes = (lower_ast_function(function),
                      lower_ir_function(lower_statement(function)))
            for route_name, qir in zip(("direct", "bridge"), routes):
                with self.subTest(case=index, route=route_name):
                    validate_function(qir)
                    with tempfile.TemporaryDirectory() as directory:
                        source = os.path.join(directory, "case.c")
                        library = os.path.join(directory, "case.so")
                        with open(source, "w", encoding="utf-8") as stream:
                            stream.write(emit_c_function(qir))
                        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                                        "-shared", "-fPIC", source, "-o", library],
                                       check=True, capture_output=True, timeout=15)
                        entry = getattr(ctypes.CDLL(library), function.name)
                        entry.argtypes = [ctypes.c_bool] * 3
                        entry.restype = ctypes.c_bool
                        for values in itertools.product((False, True), repeat=3):
                            self.assertEqual(bool(entry(*values)), bool(expected(*values)),
                                             f"{route_name}: {values}")


if __name__ == "__main__":
    unittest.main()
