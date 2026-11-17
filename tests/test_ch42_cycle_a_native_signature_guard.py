"""ABI argument type checks for QIR native calls."""
import unittest
from main import build_frontend
from frontend.quar.errors import SemanticError
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError


class NativeSignatureGuardTests(unittest.TestCase):
    def lower(self, source):
        ast, _ = build_frontend(source)
        return lower_ast_program(ast)

    def test_matching_bool_argument(self):
        self.lower('extern "C" i32 native_flag(bool value); i32 result = native_flag(true);')

    def test_matching_i32_argument(self):
        self.lower('extern "C" bool native_ready(i32 value); bool ready = native_ready(1);')

    def test_mismatched_bool_for_i32(self):
        with self.assertRaises((QIRProgramLoweringError, SemanticError)):
            self.lower('extern "C" i32 native_flag(i32 value); i32 result = native_flag(true);')

    def test_mismatched_i32_for_bool(self):
        with self.assertRaises((QIRProgramLoweringError, SemanticError)):
            self.lower('extern "C" bool native_ready(bool value); bool ready = native_ready(1);')

    def test_mismatched_void_call(self):
        with self.assertRaises((QIRProgramLoweringError, SemanticError)):
            self.lower('extern "C" void native_set(bool value); native_set(1);')


if __name__ == '__main__':
    unittest.main()
