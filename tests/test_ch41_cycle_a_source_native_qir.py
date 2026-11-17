"""Cycle A: source AST declarations lower to explicit native QIR operations."""
import ctypes.util
import unittest

from frontend.quar.ast_nodes import (ExternalFunctionDeclaration, FunctionCall,
    FunctionParameter, Integer, VariableDeclaration, Variable)
from frontend.quar.qir.program_lowering import lower_ast_program, QIRProgramLoweringError
from qrvm.qir_program_backend import compile_qir_program
from qrvm.native_ffi import NativeLibrary
from qrvm.vm import QRVM
from main import build_frontend


class NativeSourceQIRTests(unittest.TestCase):
    def source(self):
        return [ExternalFunctionDeclaration('C', 'i32', 'abs', [FunctionParameter('i32', 'x')]),
                VariableDeclaration('i32', 'result', FunctionCall('abs', [Integer(-9)])),
                FunctionCall('print', [Variable('result')])]

    def test_actual_source_frontend_to_qir(self):
        source = 'extern "C" i32 abs(i32 x); i32 result = abs(9); print(result);'
        ast, _ = build_frontend(source)
        module = lower_ast_program(ast)
        self.assertEqual(module.native_declarations, (('abs', ('i32',), 'i32'),))
        self.assertIn('native_call', [op.opcode for op in module.functions[0].blocks[0].instructions])

    def test_external_declaration_lowers_to_native_call(self):
        module = lower_ast_program(self.source())
        self.assertEqual(module.native_declarations, (('abs', ('i32',), 'i32'),))
        self.assertIn('native_call', [op.opcode for op in module.functions[0].blocks[0].instructions])
        self.assertEqual(compile_qir_program(module)['native_declarations'], {'abs': (('i32',), 'i32')})

    def test_real_c_library_executes(self):
        libc = ctypes.util.find_library('c')
        if libc is None:
            self.skipTest('C library not available')
        package = compile_qir_program(lower_ast_program(self.source()))
        vm = QRVM()
        vm.bind_native(package['native_declarations'], NativeLibrary(libc))
        vm.run(package)
        self.assertEqual(vm.stack, [])

    def test_native_void_call(self):
        source = [ExternalFunctionDeclaration('C', 'void', 'noop', []), FunctionCall('noop', [])]
        module = lower_ast_program(source)
        self.assertEqual(module.functions[0].blocks[0].instructions[0].opcode, 'native_call_void')

    def test_opaque_native_type_is_supported(self):
        source = [ExternalFunctionDeclaration('C', 'opaque', 'get_pointer', []), FunctionCall('print', [Integer(1)])]
        self.assertEqual(lower_ast_program(source).native_declarations[0][2], "opaque")

    def test_duplicate_native_symbol_fails_closed(self):
        source = self.source()
        with self.assertRaisesRegex(QIRProgramLoweringError, 'Unsupported or conflicting native'):
            lower_ast_program([source[0], source[0], *source[1:]])


if __name__ == '__main__':
    unittest.main()
