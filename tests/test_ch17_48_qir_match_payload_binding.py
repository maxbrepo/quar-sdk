"""Execute guarded enum match bindings through both lowering paths and C."""
import ctypes
import os
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (BinaryOperation, EnumDefinition, EnumVariant,
    FunctionDefinition, FunctionParameter, IfStatement, Integer, MatchArm, MatchStatement,
    ReturnStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from frontend.quar.qir.enum_layout import lower_enum_layout
from frontend.quar.qir.c_backend import emit_c_function


class MatchPayloadBindingTests(unittest.TestCase):
    def setUp(self):
        self.layout = lower_enum_layout(EnumDefinition("Result", [
            EnumVariant("Ok", ["i32", "bool"]), EnumVariant("Error", ["i32"]),
            EnumVariant("Empty", [])]))
        self.params = [FunctionParameter("i32", "tag"),
                       FunctionParameter("i32", "payload_0_0"),
                       FunctionParameter("bool", "payload_0_1"),
                       FunctionParameter("i32", "payload_1_0")]
        self.match = MatchStatement(Variable("tag"), [
            MatchArm("Ok", ["number", "flag"], [IfStatement(Variable("flag"), [ReturnStatement(Variable("number"))], [ReturnStatement(Integer(-2))])]),
            MatchArm("Error", ["error"], [ReturnStatement(BinaryOperation(Variable("error"), "+", Integer(1)))]),
            MatchArm("Empty", [], [ReturnStatement(Integer(0))])],
            [ReturnStatement(Integer(-1))])

    def function(self):
        return FunctionDefinition("i32", "match_payload", self.params, [self.match])

    def routes(self):
        function = self.function()
        return (lower_ast_function(function, enum_layout=self.layout),
                lower_ir_function(lower_statement(function), enum_layout=self.layout))

    def test_compiled_match_bindings_both_routes(self):
        for index, function in enumerate(self.routes()):
            with self.subTest(route=index), tempfile.TemporaryDirectory() as directory:
                source = os.path.join(directory, "match.c")
                library = os.path.join(directory, "match.so")
                with open(source, "w", encoding="utf-8") as handle:
                    handle.write(emit_c_function(function))
                subprocess.run(["cc", "-std=c99", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
                                source, "-o", library], check=True, capture_output=True)
                compiled = ctypes.CDLL(library).match_payload
                compiled.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_bool, ctypes.c_int32]
                compiled.restype = ctypes.c_int32
                self.assertEqual([compiled(tag, 42, True, 9) for tag in (0, 1, 2, -1, 99)],
                                 [42, 10, 0, -1, -1])

    def test_missing_payload_slot_rejected(self):
        self.params.pop(1)
        with self.assertRaisesRegex(QIRASTLoweringError, "payload slot"):
            lower_ast_function(self.function(), enum_layout=self.layout)
        with self.assertRaisesRegex(QIRBridgeError, "payload slot"):
            lower_ir_function(lower_statement(self.function()), enum_layout=self.layout)

    def test_binding_shadow_rejected(self):
        self.params.append(FunctionParameter("i32", "number"))
        with self.assertRaisesRegex(QIRASTLoweringError, "shadows"):
            lower_ast_function(self.function(), enum_layout=self.layout)
        with self.assertRaisesRegex(QIRBridgeError, "shadows"):
            lower_ir_function(lower_statement(self.function()), enum_layout=self.layout)


if __name__ == "__main__":
    unittest.main()
