"""Build artifact hygiene and actionable failures."""
import shutil
import tempfile
import unittest
from pathlib import Path
from frontend.quar.ir import lower_program_project
from frontend.quar.module_loader import ModuleLoader
from tooling.ir_build import CLayout, BuildError, emit_c, compile_objects, link_executable


class IRBuildHygieneTests(unittest.TestCase):
    def test_switch_layout_removes_only_tracked_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'main.vq').write_text('int answer() { return 42; }\nreturn answer();\n')
            loader = ModuleLoader(root)
            loader.load(root / 'main.vq')
            project = lower_program_project(loader, root / 'main.vq')
            output = root / 'out'
            split = emit_c(project, output, CLayout.SPLIT)
            (output / 'user_notes.txt').write_text('keep')
            single = emit_c(project, output, CLayout.SINGLE)
            self.assertEqual(len(single.sources), 1)
            self.assertFalse(any(path.exists() for path in split.sources))
            self.assertFalse(any(path.exists() for path in split.headers))
            self.assertEqual((output / 'user_notes.txt').read_text(), 'keep')

    def test_missing_compiler_reports_build_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.c'
            source.write_text('int x;')
            from tooling.ir_build import CArtifacts
            artifacts = CArtifacts(CLayout.SINGLE, (source,), ())
            with self.assertRaisesRegex(BuildError, 'compilation failed'):
                compile_objects(artifacts, root, compiler='quar_nonexistent_cc')

    def test_failed_link_does_not_leave_old_executable(self):
        if not shutil.which('gcc'):
            self.skipTest('gcc unavailable')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / 'app'
            executable.write_text('stale executable')
            obj = root / 'empty.o'
            obj.write_text('invalid object')
            with self.assertRaisesRegex(BuildError, 'linking failed'):
                link_executable((obj,), executable)
            self.assertFalse(executable.exists())

if __name__ == '__main__':
    unittest.main()
