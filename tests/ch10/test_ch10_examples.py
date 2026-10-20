"""Run Chapter 10 examples without interactive input or project filesystem changes."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / 'examples/0.0.4/typed/10 file io'
EXPECTATIONS = Path(__file__).with_name('ch10_example_expectations.json')

class Chapter10Examples(unittest.TestCase):
    def test_all_examples(self):
        expected = json.loads(EXPECTATIONS.read_text(encoding='utf-8'))
        actual = {p.name for p in EXAMPLES.glob('*.vq')}
        self.assertEqual(actual, set(expected))
        for name, oracle in sorted(expected.items()):
            with self.subTest(example=name):
                source = (EXAMPLES / name).read_text(encoding='utf-8')
                self.assertEqual(hashlib.sha256(source.encode()).hexdigest(), oracle['source_sha256'])
                with tempfile.TemporaryDirectory(prefix='quar-ch10-') as temp:
                    previous = Path.cwd()
                    output = io.StringIO()
                    try:
                        os.chdir(temp)
                        with contextlib.redirect_stdout(output):
                            try:
                                tree = Parser(Lexer(source).tokenize()).parse()
                                checked = SemanticAnalyzer().analyze(tree)
                                program = QRVMCompiler().compile(checked)
                                QRVM().run(program)
                            except Exception as exc:
                                if oracle['error_type'] is None:
                                    raise
                                self.assertEqual(type(exc).__name__, oracle['error_type'])
                            else:
                                self.assertIsNone(oracle['error_type'], 'Expected error not raised')
                    finally:
                        os.chdir(previous)
                    if oracle['stdout'] is not None:
                        self.assertEqual(output.getvalue(), oracle['stdout'])
