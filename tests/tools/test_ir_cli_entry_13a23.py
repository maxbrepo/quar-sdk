"""CLI emission and C layout parity for executable IR programs."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from main import emit_ir_c_sources, parse_c_layout_option
from tooling.ir_build import CLayout, compile_objects, link_executable


class IRCLIEntry13A23Tests(unittest.TestCase):
    def test_cli_emits_executable_in_both_layouts(self):
        if not shutil.which("gcc"):
            self.skipTest("gcc unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "lib.vq").write_text("int answer() { return 42; }\n", encoding="utf-8")
            source = root / "main.vq"
            source.write_text("import lib as l;\nreturn l.answer() + l.answer();\n", encoding="utf-8")
            for layout in CLayout:
                with self.subTest(layout=layout):
                    _, selected = parse_c_layout_option(["-f", str(source), "--c-layout", layout.value])
                    output = root / layout.value
                    artifacts = emit_ir_c_sources(source, selected, output)
                    self.assertEqual(len(artifacts.sources), 1 if layout is CLayout.SINGLE else 2)
                    objects = compile_objects(artifacts, output)
                    binary = link_executable(objects, output / "app")
                    result = subprocess.run([str(binary)], check=False, capture_output=True)
                    self.assertEqual(result.returncode, 84, result.stderr)

if __name__ == "__main__":
    unittest.main()
