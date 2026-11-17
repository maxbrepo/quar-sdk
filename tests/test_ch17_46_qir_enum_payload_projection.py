"""Compile and execute an explicitly flattened payload projection."""
import ctypes
import os
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import EnumDefinition, EnumVariant
from frontend.quar.ir.model import IREnumDefinition, IREnumVariant
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.enum_layout import QIREnumLayoutError, lower_enum_layout
from frontend.quar.qir.enum_payload_lowering import lower_payload_projection
from frontend.quar.qir.enum_runtime import construct_enum_value


class EnumPayloadProjectionTests(unittest.TestCase):
    def setUp(self):
        self.layout = lower_enum_layout(EnumDefinition("Result", [
            EnumVariant("Ok", ["i32", "bool"]),
            EnumVariant("Error", ["i32"]),
            EnumVariant("Empty", []),
        ]))

    def test_compiled_projection_and_inactive_variant(self):
        for layout in (self.layout, lower_enum_layout(IREnumDefinition("Result", (
            IREnumVariant("Ok", ("i32", "bool")),
            IREnumVariant("Error", ("i32",)),
            IREnumVariant("Empty", ()),
        )))):
            with self.subTest(layout=layout), tempfile.TemporaryDirectory() as directory:
                function = lower_payload_projection("get_ok", layout, "Ok", 0, -1)
                source = os.path.join(directory, "enum.c")
                library = os.path.join(directory, "enum.so")
                with open(source, "w", encoding="utf-8") as handle:
                    handle.write(emit_c_function(function))
                subprocess.run(["cc", "-std=c99", "-shared", "-fPIC", "-Wall", "-Wextra",
                                "-Werror", "-Wno-unused-parameter", source, "-o", library],
                               capture_output=True, check=True)
                compiled = ctypes.CDLL(library).get_ok
                compiled.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_bool, ctypes.c_int32]
                compiled.restype = ctypes.c_int32
                value = construct_enum_value(layout, "Ok", (42, True))
                self.assertEqual(compiled(value.tag, 42, True, 0), 42)
                self.assertEqual(compiled(1, 999, False, 7), -1)
                self.assertEqual(compiled(2, 999, False, 7), -1)
                self.assertEqual(compiled(-1, 999, False, 7), -1)

    def test_reject_invalid_field_and_default(self):
        for field in (-1, 2, True):
            with self.subTest(field=field), self.assertRaises(QIREnumLayoutError):
                lower_payload_projection("bad", self.layout, "Ok", field, -1)
        with self.assertRaises(QIREnumLayoutError):
            lower_payload_projection("bad", self.layout, "Ok", 1, -1)
        with self.assertRaises(QIREnumLayoutError):
            lower_payload_projection("bad", self.layout, "Ok", 0, 2**31)

    def test_reject_unsupported_payload_type(self):
        layout = lower_enum_layout(EnumDefinition("Other", [EnumVariant("Text", ["string"])]))
        with self.assertRaises(QIREnumLayoutError):
            lower_payload_projection("bad", layout, "Text", 0, 0)


if __name__ == "__main__":
    unittest.main()
