"""Process-isolated runtime bounds checks across both source-to-QIR routes."""
import subprocess
import tempfile
import unittest
from pathlib import Path

from frontend.quar.ast_nodes import (ArrayAccess, ArrayDeclaration, FunctionCall,
    FunctionDefinition, Integer, ReturnStatement, String)
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function
from frontend.quar.qir.legacy_bridge import lower_ir_function
from frontend.quar.qir.c_backend import emit_c_function


class UnicodeArrayBoundsTests(unittest.TestCase):
    def check_routes(self, body, expected_exit):
        function = FunctionDefinition('i32', 'bounds_demo', [], body)
        for route, qir in (
            ('ast', lower_ast_function(function)),
            ('legacy', lower_ir_function(lower_statement(function))),
        ):
            with self.subTest(route=route):
                source = emit_c_function(qir)
                with tempfile.TemporaryDirectory() as folder:
                    path = Path(folder)
                    (path / 'test.c').write_text(source + '\nint main(void) { return bounds_demo(); }\n')
                    subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                                    str(path / 'test.c'), '-o', str(path / 'test')],
                                   check=True, capture_output=True)
                    # Disable core dumps for deliberate abort tests.
                    import resource
                    def disable_core():
                        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                    result = subprocess.run([str(path / 'test')], capture_output=True,
                                            preexec_fn=disable_core)
                    if expected_exit == 'trap':
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(result.returncode, -6)  # SIGABRT on Linux
                    else:
                        self.assertEqual(result.returncode, expected_exit)

    def test_unicode_valid_multibyte_index(self):
        self.check_routes([ReturnStatement(FunctionCall('__qir_utf8_scalar_at',
            [String('aé😀'), Integer(1)]))], 233)

    def test_unicode_negative_index_traps(self):
        self.check_routes([ReturnStatement(FunctionCall('__qir_utf8_scalar_at',
            [String('aé😀'), Integer(-1)]))], 'trap')

    def test_unicode_index_equal_to_length_traps(self):
        self.check_routes([ReturnStatement(FunctionCall('__qir_utf8_scalar_at',
            [String('aé😀'), Integer(3)]))], 'trap')

    def test_unicode_empty_string_access_traps(self):
        self.check_routes([ReturnStatement(FunctionCall('__qir_utf8_scalar_at',
            [String(''), Integer(0)]))], 'trap')

    def test_array_valid_index(self):
        self.check_routes([ArrayDeclaration('i32', 'items', 2, [Integer(4), Integer(7)]),
                           ReturnStatement(ArrayAccess('items', Integer(1)))], 7)

    def test_array_negative_index_traps(self):
        self.check_routes([ArrayDeclaration('i32', 'items', 2, [Integer(4), Integer(7)]),
                           ReturnStatement(ArrayAccess('items', Integer(-1)))], 'trap')

    def test_array_index_equal_to_capacity_traps(self):
        self.check_routes([ArrayDeclaration('i32', 'items', 2, [Integer(4), Integer(7)]),
                           ReturnStatement(ArrayAccess('items', Integer(2)))], 'trap')


if __name__ == '__main__':
    unittest.main()
