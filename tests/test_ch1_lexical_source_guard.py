"""Real .vq syntax fixtures for the opt-in shared lexical backend path."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.c.codegen import CCodeGenerator
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"typed": ["3", "1"], "inferred": ["3", "2"], "mixed": ["3", "4", "1"]}

class LexicalSourceGuardTests(unittest.TestCase):
    def test_real_sources_compile_with_shared_storage(self):
        for profile, expected in EXPECTED.items():
            with self.subTest(profile=profile):
                path = ROOT / "tests/fixtures/ch1_lexical_experimental" / profile / "ch1 lexical syntax guard.vq"
                program = Parser(Lexer(path.read_text(encoding="utf-8")).tokenize()).parse()
                allow_inference = profile != "typed"
                bytecode = QRVMCompiler().compile(program, lexical=True, allow_inference=allow_inference)
                stores = [operand for opcode, operand in bytecode["instructions"] if opcode == OpCode.STORE]
                self.assertTrue(stores)
                self.assertTrue(all(name.startswith("__vq_binding_") for name in stores))
                c_source = CCodeGenerator().generate(program, lexical=True, allow_inference=allow_inference)
                for name in set(stores):
                    self.assertIn(name, c_source)
                if shutil.which("cc"):
                    with tempfile.TemporaryDirectory() as directory:
                        c_path = Path(directory) / "test.c"
                        exe = Path(directory) / "test"
                        c_path.write_text(c_source, encoding="utf-8")
                        built = subprocess.run(["cc", "-std=c11", "-Wall", "-Werror", str(c_path), "-o", str(exe)], capture_output=True, text=True)
                        self.assertEqual(built.returncode, 0, built.stderr)
                        result = subprocess.run([str(exe)], capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stdout.splitlines(), expected)

if __name__ == "__main__":
    unittest.main()
