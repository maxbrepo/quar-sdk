"""Execute payload-free match arms through both QIR lowering routes."""
import ctypes
import os
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import (EnumDefinition, EnumVariant, FunctionDefinition,
    FunctionParameter, Integer, MatchArm, MatchStatement, ReturnStatement, Variable)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from frontend.quar.qir.enum_layout import lower_enum_layout
from frontend.quar.qir.c_backend import emit_c_function


class MatchTagIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.layout = lower_enum_layout(EnumDefinition("State", [
            EnumVariant("Pending", []), EnumVariant("Running", []), EnumVariant("Done", [])]))
        self.function = FunctionDefinition("i32", "select_state", [FunctionParameter("i32", "tag")], [
            MatchStatement(Variable("tag"), [
                MatchArm("Pending", [], [ReturnStatement(Integer(11))]),
                MatchArm("Running", [], [ReturnStatement(Integer(22))]),
                MatchArm("Done", [], [ReturnStatement(Integer(33))])],
                [ReturnStatement(Integer(-1))])])

    def test_both_routes_execute_all_arms_and_invalid_tag(self):
        routes = (lower_ast_function(self.function, enum_layout=self.layout),
                  lower_ir_function(lower_statement(self.function), enum_layout=self.layout))
        for index, function in enumerate(routes):
            with self.subTest(route=index), tempfile.TemporaryDirectory() as directory:
                source = os.path.join(directory, "match.c")
                library = os.path.join(directory, "match.so")
                with open(source, "w", encoding="utf-8") as handle:
                    handle.write(emit_c_function(function))
                subprocess.run(["cc", "-std=c99", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
                                source, "-o", library], capture_output=True, check=True)
                compiled = ctypes.CDLL(library).select_state
                compiled.argtypes = [ctypes.c_int32]
                compiled.restype = ctypes.c_int32
                self.assertEqual([compiled(tag) for tag in (0, 1, 2, -1, 99)], [11, 22, 33, -1, -1])

    def test_requires_explicit_invalid_tag_fallback(self):
        self.function.body[0].default_body = []
        with self.assertRaisesRegex(QIRASTLoweringError, "default"):
            lower_ast_function(self.function, enum_layout=self.layout)
        with self.assertRaisesRegex(QIRBridgeError, "default"):
            lower_ir_function(lower_statement(self.function), enum_layout=self.layout)

    def test_payload_layout_rejected(self):
        layout = lower_enum_layout(EnumDefinition("Option", [EnumVariant("Some", ["i32"])]))
        with self.assertRaisesRegex(QIRASTLoweringError, "Unknown variant"):
            lower_ast_function(self.function, enum_layout=layout)
        with self.assertRaisesRegex(QIRBridgeError, "Unknown variant"):
            lower_ir_function(lower_statement(self.function), enum_layout=layout)


if __name__ == "__main__":
    unittest.main()
