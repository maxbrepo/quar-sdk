"""Compile source string literals through both QIR lowering routes."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import FunctionDefinition, ReturnStatement, String
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class CString(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_uint8)), ("length", ctypes.c_size_t)]


class SourceStringTests(unittest.TestCase):
    def test_literal_round_trip_through_c(self):
        for sample in ("", "abc", "aé😀", "a\x00b", "e\u0301"):
            function = FunctionDefinition("string", "string_demo", [], [ReturnStatement(String(sample))])
            routes = (lower_ast_function(function), lower_ir_function(lower_statement(function)))
            for route in routes:
                with self.subTest(sample=sample, route=route):
                    source = emit_c_function(route)
                    with tempfile.TemporaryDirectory() as folder:
                        path = Path(folder)
                        (path / "demo.c").write_text(source)
                        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "demo.c", "-o", "demo.so"], cwd=path, check=True, capture_output=True)
                        lib = ctypes.CDLL(str(path / "demo.so"))
                        lib.string_demo.restype = CString
                        result = lib.string_demo()
                        self.assertEqual(ctypes.string_at(result.data, result.length), sample.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
