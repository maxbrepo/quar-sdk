"""Executable module-call tests for the initial i32 QIR C adapter."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QModule, QReturn, QType, QValue
from frontend.quar.qir.module_c_backend import emit_c_module

I32 = QType('i32')


def sample_module():
    x = QValue('x', I32)
    one = QValue('one', I32)
    plus = QValue('plus', I32)
    helper = QFunction('helper', I32, (x,), (QBlock('entry', (
        QInstruction('const', (), one, immediate=1),
        QInstruction('add', (x, one), plus),
    ), QReturn(plus)),))
    arg = QValue('arg', I32)
    first = QValue('first', I32)
    second = QValue('second', I32)
    caller = QFunction('caller', I32, (arg,), (QBlock('entry', (
        QInstruction('call', (arg,), first, immediate='helper'),
        QInstruction('call', (first,), second, immediate='helper'),
    ), QReturn(second)),))
    return QModule('sample', (caller, helper))


class QIRModuleCTests(unittest.TestCase):
    def test_emits_prototypes_and_calls(self):
        source = emit_c_module(sample_module())
        self.assertIn('int32_t helper(int32_t qv_0);', source)
        self.assertIn('= helper(', source)

    @unittest.skipUnless(shutil.which('gcc'), 'gcc required')
    def test_compiles_and_executes_two_calls(self):
        source = emit_c_module(sample_module())
        with tempfile.TemporaryDirectory() as tmp:
            c_path = Path(tmp) / 'module.c'
            binary = Path(tmp) / 'module'
            c_path.write_text(source + '\nint main(void) { return caller(11) == 13 ? 0 : 1; }\n', encoding='utf-8')
            build = subprocess.run(['gcc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(c_path), '-o', str(binary)], capture_output=True, text=True, timeout=20)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
