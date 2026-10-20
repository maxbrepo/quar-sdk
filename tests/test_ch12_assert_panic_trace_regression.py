"""Regression coverage for chapter 12 assertion, panic, and error traces."""
import contextlib
import io
import unittest
from pathlib import Path

from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM, QuarPanic


EXAMPLES = Path(__file__).resolve().parents[1] / 'examples/0.0.4/typed/12 error handling'


class Chapter12RuntimeRegression(unittest.TestCase):
    def execute_example(self, number):
        source = next(EXAMPLES.glob(f'{number} *')).read_text(encoding='utf-8')
        program, _ = build_frontend(source)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            QRVM().run(QRVMCompiler().compile(program))
        return output.getvalue()

    def test_assert_success_and_recovery(self):
        self.assertEqual(self.execute_example(221).strip(), 'ok')
        for number in (222, 231):
            self.assertIn('Assertion failed', self.execute_example(number))

    def test_assert_failure(self):
        with self.assertRaisesRegex(RuntimeError, 'Assertion failed'):
            self.execute_example(225)

    def test_panic_is_fatal_and_bypasses_catch(self):
        for number in (228, 229):
            with self.assertRaises(QuarPanic):
                self.execute_example(number)

    def test_invalid_assert_and_panic_arguments(self):
        from frontend.quar.semantic import SemanticError

        expected = {
            226: "assert argument must be a boolean",
            227: "assert expects one boolean argument",
            232: "panic message must be a string",
            233: "panic expects one string argument",
        }
        for number, message in expected.items():
            with self.subTest(example=number):
                source = next(EXAMPLES.glob(f'{number} *')).read_text(encoding='utf-8')
                with self.assertRaisesRegex(SemanticError, message):
                    build_frontend(source)

    def test_error_trace_includes_function_frames(self):
        trace = self.execute_example(223)
        self.assertIn('outer', trace)
        self.assertIn('inner', trace)
        self.assertIn('<main>', self.execute_example(224))


if __name__ == '__main__':
    unittest.main()
