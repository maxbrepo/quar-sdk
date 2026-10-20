"""C lexical inference uses the same storage identities as QRVM."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from frontend.quar.ast_nodes import Assignment, Boolean, FunctionCall, IfStatement, Integer, Variable
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode


class CLexicalInferenceTests(unittest.TestCase):
    def program(self):
        return [
            Assignment('x', Integer(1)),
            IfStatement(Boolean(True), [
                Assignment('x', Integer(2)),
                Assignment('y', Integer(3)),
                FunctionCall('print', [Variable('y')]),
            ], []),
            FunctionCall('print', [Variable('x')]),
        ]

    def test_inferred_storage_matches_qrvm(self):
        program = self.program()
        source = CCodeGenerator().generate(program, lexical=True, allow_inference=True)
        instructions = QRVMCompiler().compile(program, lexical=True, allow_inference=True)['instructions']
        stores = [value for opcode, value in instructions if opcode == OpCode.STORE]
        self.assertEqual(stores[0], stores[1])
        self.assertNotEqual(stores[0], stores[2])
        self.assertIn('int32_t ' + stores[0] + ' = 1;', source)
        self.assertIn(stores[0] + ' = 2;', source)
        self.assertIn('int32_t ' + stores[2] + ' = 3;', source)
        self.assertEqual(program[0].name, 'x')

    def test_inference_is_opt_in(self):
        with self.assertRaises(NameError):
            CCodeGenerator().generate([Assignment('x', Integer(1))], lexical=True)

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_inferred_program_compiles_and_runs(self):
        source = CCodeGenerator().generate(self.program(), lexical=True, allow_inference=True)
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / 'inference.c'
            executable = Path(directory) / 'inference'
            source_path.write_text(source, encoding='utf-8')
            build = subprocess.run(['cc', '-std=c11', '-Wall', '-Werror', str(source_path), '-o', str(executable)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            result = subprocess.run([str(executable)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ['3', '2'])


if __name__ == '__main__':
    unittest.main()
