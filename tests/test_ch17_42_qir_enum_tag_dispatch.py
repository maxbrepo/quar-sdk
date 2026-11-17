"""Exercise the initial payload-free enum tag dispatch primitive."""
import ctypes
import os
import subprocess
import tempfile
import unittest

from frontend.quar.ast_nodes import EnumDefinition, EnumVariant
from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.enum_layout import QIREnumLayoutError, lower_enum_layout
from frontend.quar.qir.enum_tag_lowering import lower_tag_dispatch


class QIREnumTagDispatchTests(unittest.TestCase):
    def setUp(self):
        self.layout = lower_enum_layout(EnumDefinition("State", [
            EnumVariant("Pending", []), EnumVariant("Running", []), EnumVariant("Done", [])
        ]))

    def test_exhaustive_dispatch_executes(self):
        function = lower_tag_dispatch("state_result", self.layout, {
            "Pending": 11, "Running": 22, "Done": 33
        })
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "dispatch.c")
            library = os.path.join(directory, "dispatch.so")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write(emit_c_function(function))
            subprocess.run(["cc", "-std=c99", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror", source, "-o", library], check=True, capture_output=True)
            compiled = ctypes.CDLL(library).state_result
            compiled.argtypes = [ctypes.c_int32]
            compiled.restype = ctypes.c_int32
            self.assertEqual([compiled(tag) for tag in range(3)], [11, 22, 33])

    def test_non_exhaustive_dispatch_rejected(self):
        with self.assertRaisesRegex(QIREnumLayoutError, "Non-exhaustive"):
            lower_tag_dispatch("incomplete", self.layout, {"Pending": 1})

    def test_unknown_arm_rejected(self):
        with self.assertRaisesRegex(QIREnumLayoutError, "Unknown"):
            lower_tag_dispatch("unknown", self.layout, {"Missing": 1}, default=0)

    def test_payload_variants_rejected(self):
        layout = lower_enum_layout(EnumDefinition("Option", [EnumVariant("None", []), EnumVariant("Some", ["i32"])]))
        with self.assertRaisesRegex(QIREnumLayoutError, "Payload"):
            lower_tag_dispatch("option", layout, {"None": 0, "Some": 1})


if __name__ == "__main__":
    unittest.main()
