"""End-to-end parity and repeatability checks for experimental IR C layouts."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from main import emit_ir_c_sources
from tooling.ir_build import CLayout, compile_objects, link_executable


@unittest.skipUnless(shutil.which('gcc'), 'GCC required for end-to-end checks')
class IRRegression13A25Tests(unittest.TestCase):
    def test_diamond_project_same_exit_status_in_both_layouts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'shared.vq').write_text('int answer() { return 42; }\n', encoding='utf-8')
            (root / 'left.vq').write_text('import shared as s;\nint left() { return s.answer(); }\n', encoding='utf-8')
            (root / 'right.vq').write_text('import shared as t;\nint right() { return t.answer(); }\n', encoding='utf-8')
            source = root / 'main.vq'
            source.write_text('import left as l;\nimport right as r;\nreturn l.left() + r.right();\n', encoding='utf-8')
            outcomes = {}
            for layout in CLayout:
                with self.subTest(layout=layout.value):
                    output = root / layout.value
                    artifacts = emit_ir_c_sources(source, layout, output)
                    objects = compile_objects(artifacts, output)
                    executable = link_executable(objects, output / 'app')
                    result = subprocess.run([str(executable)], capture_output=True, check=False)
                    outcomes[layout] = (result.returncode, result.stdout, result.stderr)
            self.assertEqual(outcomes[CLayout.SINGLE], outcomes[CLayout.SPLIT])
            self.assertEqual(outcomes[CLayout.SINGLE][0], 84)

    def test_switch_layout_and_rebuild_in_same_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'main.vq'
            source.write_text('int answer() { return 42; }\nreturn answer();\n', encoding='utf-8')
            output = root / 'generated'
            sentinel = output / 'my_document.txt'
            results = []
            for layout in (CLayout.SPLIT, CLayout.SINGLE, CLayout.SPLIT):
                artifacts = emit_ir_c_sources(source, layout, output)
                if not sentinel.exists():
                    sentinel.write_text('preserve me', encoding='utf-8')
                objects = compile_objects(artifacts, output)
                executable = link_executable(objects, output / 'app')
                results.append(subprocess.run([str(executable)], capture_output=True).returncode)
                self.assertEqual(sentinel.read_text(encoding='utf-8'), 'preserve me')
                self.assertTrue(all(path.exists() for path in artifacts.sources))
            self.assertEqual(results, [42, 42, 42])


if __name__ == '__main__':
    unittest.main()
