"""Exercise UTF-8 string variables across both source lowering routes and C."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import Assignment, FunctionDefinition, ReturnStatement, String, Variable, VariableDeclaration
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class CString(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_uint8)), ("length", ctypes.c_size_t)]


class StringVariablesTests(unittest.TestCase):
    def test_local_string_reassignment(self):
        for initial, replacement in (("first", "aé😀"), ("a\x00b", ""), ("", "e\u0301")):
            function = FunctionDefinition("string", "string_variable", [], [
                VariableDeclaration("string", "message", String(initial)),
                Assignment("message", String(replacement)),
                ReturnStatement(Variable("message")),
            ])
            routes = (lower_ast_function(function), lower_ir_function(lower_statement(function)))
            for route in routes:
                with self.subTest(initial=initial, replacement=replacement, route=route):
                    source = emit_c_function(route)
                    with tempfile.TemporaryDirectory() as folder:
                        path = Path(folder)
                        (path / "demo.c").write_text(source, encoding="utf-8")
                        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "demo.c", "-o", "demo.so"], cwd=path, check=True, capture_output=True)
                        lib = ctypes.CDLL(str(path / "demo.so"))
                        lib.string_variable.restype = CString
                        result = lib.string_variable()
                        self.assertEqual(ctypes.string_at(result.data, result.length), replacement.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
