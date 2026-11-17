"""Native bool signatures through source lowering, QIR and QRVM."""
import unittest
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from main import build_frontend

class NativeBoolQIRTests(unittest.TestCase):
    def lower(self, source):
        ast, _ = build_frontend(source)
        return lower_ast_program(ast)

    def test_bool_return_and_variable(self):
        module = self.lower('extern "C" bool native_ready(i32 flags); bool ready = native_ready(1); print(ready);')
        self.assertEqual(module.native_declarations, (('native_ready', ('i32',), 'bool'),))
        self.assertEqual(compile_qir_program(module)['native_declarations']['native_ready'], (('i32',), 'bool'))

    def test_bool_argument(self):
        module = self.lower('extern "C" i32 native_flag(bool value); i32 result = native_flag(true); print(result);')
        self.assertEqual(module.native_declarations, (('native_flag', ('bool',), 'i32'),))
        self.assertIn('native_call', [i.opcode for i in module.functions[0].blocks[0].instructions])
        compile_qir_program(module)

    def test_bool_void_argument(self):
        module = self.lower('extern "C" void native_set(bool value); native_set(false);')
        self.assertEqual(module.native_declarations, (('native_set', ('bool',), 'void'),))
        compile_qir_program(module)

    def test_opaque_abi_declaration(self):
        module = self.lower('extern "C" opaque native_pointer(); print(1);')
        self.assertEqual(module.native_declarations[0][2], "opaque")

if __name__ == '__main__':
    unittest.main()
