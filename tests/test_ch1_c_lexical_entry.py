"""Opt-in C backend lexical lowering parity with QRVM."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from frontend.quar.ast_nodes import (
    Assignment, Boolean, FunctionCall, IfStatement, Integer,
    Variable, VariableDeclaration,
)
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode


class CLexicalEntryTests(unittest.TestCase):
    def program(self):
        return [
            VariableDeclaration('int', 'x', Integer(1)),
            IfStatement(Boolean(True), [
                VariableDeclaration('int', 'x', Integer(2)),
                Assignment('x', Integer(3)),
                FunctionCall('print', [Variable('x')]),
            ], []),
            FunctionCall('print', [Variable('x')]),
        ]

    def test_lexical_names_match_qrvm_and_preserve_source(self):
        program = self.program()
        c_source = CCodeGenerator().generate(program, lexical=True)
        bytecode = QRVMCompiler().compile(program, lexical=True)['instructions']
        stores = [operand for opcode, operand in bytecode if opcode == OpCode.STORE]
        self.assertEqual(len(stores), 3)
        self.assertNotEqual(stores[0], stores[1])
        self.assertEqual(stores[1], stores[2])
        for storage_name in set(stores):
            self.assertIn(storage_name, c_source)
        self.assertEqual(program[0].name, 'x')
        self.assertEqual(program[1].then_body[0].name, 'x')

    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_shadowed_program_compiles_and_runs(self):
        source = CCodeGenerator().generate(self.program(), lexical=True)
        with tempfile.TemporaryDirectory() as directory:
            c_path = Path(directory) / 'shadow.c'
            exe_path = Path(directory) / 'shadow'
            c_path.write_text(source, encoding='utf-8')
            built = subprocess.run(['cc', '-std=c11', '-Wall', '-Werror', str(c_path), '-o', str(exe_path)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            run = subprocess.run([str(exe_path)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.splitlines(), ['3', '1'])

    def test_unsupported_node_fails_explicitly(self):
        with self.assertRaises(NotImplementedError):
            CCodeGenerator().generate([object()], lexical=True)


if __name__ == '__main__':
    unittest.main()
