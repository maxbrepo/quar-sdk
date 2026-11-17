"""Verify internal Unicode scalar intrinsics through both lowering routes."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import FunctionCall, FunctionDefinition, Integer, ReturnStatement, String
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class UnicodeIntrinsicLoweringTests(unittest.TestCase):
    def run_source(self, name, args):
        ast = FunctionDefinition("int", "unicode_demo", [], [ReturnStatement(FunctionCall(name, args))])
        functions = (lower_ast_function(ast), lower_ir_function(lower_statement(ast)))
        results = []
        for function in functions:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                (path / "demo.c").write_text(emit_c_function(function), encoding="utf-8")
                subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "demo.c", "-o", "demo.so"], cwd=path, check=True, capture_output=True)
                library = ctypes.CDLL(str(path / "demo.so"))
                library.unicode_demo.restype = ctypes.c_int32
                results.append(library.unicode_demo())
        return results

    def test_unicode_scalar_length(self):
        for value in ("", "abc", "aé😀", "e\u0301", "a\x00b"):
            with self.subTest(value=value):
                self.assertEqual(self.run_source("__qir_utf8_scalar_len", [String(value)]), [len(value)] * 2)

    def test_unicode_scalar_index(self):
        sample = "aé😀"
        for index, character in enumerate(sample):
            with self.subTest(index=index):
                self.assertEqual(self.run_source("__qir_utf8_scalar_at", [String(sample), Integer(index)]), [ord(character)] * 2)

    def test_invalid_intrinsic_arity_fails_closed(self):
        ast = FunctionDefinition("int", "unicode_demo", [], [ReturnStatement(FunctionCall("__qir_utf8_scalar_at", [String("a")]))])
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(ast)
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(ast))


if __name__ == "__main__":
    unittest.main()
