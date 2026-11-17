"""Cycle A/A03: typed integer boundary execution and semantic rejection."""
import contextlib
import io
import unittest

from frontend.quar.errors import SemanticError
from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from frontend.quar.numeric_types import INTEGER_BITS, integer_range


class TypedNumericBoundariesA03(unittest.TestCase):
    def test_integer_minimum_and_maximum_execute(self):
        """Every canonical integer type must preserve both endpoints in QRVM output."""
        for type_name in INTEGER_BITS:
            minimum, maximum = integer_range(type_name)
            for value in (minimum, maximum):
                with self.subTest(type=type_name, value=value):
                    program, _ = build_frontend(f'{type_name} value = {value}; print(value);')
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        QRVM().run(QRVMCompiler().compile(program))
                    self.assertEqual(output.getvalue(), f'{value}\n')

    def test_out_of_range_literals_rejected(self):
        """Out-of-range literals must fail before compilation or execution."""
        for type_name in INTEGER_BITS:
            minimum, maximum = integer_range(type_name)
            for value in (minimum - 1, maximum + 1):
                with self.subTest(type=type_name, value=value):
                    with self.assertRaises(SemanticError):
                        build_frontend(f'{type_name} value = {value};')

    def test_unsafe_variable_narrowing_rejected(self):
        """A value fitting today does not make a narrowing variable conversion safe."""
        for source_type, target_type in [('i16', 'i8'), ('u16', 'u8'), ('i32', 'i16'), ('u8', 'i8')]:
            with self.subTest(source=source_type, target=target_type):
                with self.assertRaises(SemanticError):
                    build_frontend(f'{source_type} source = 7; {target_type} target = source;')


if __name__ == '__main__':
    unittest.main()
