"""Regression checks for the conservative IR runtime corpus audit."""
import tempfile
import unittest
from pathlib import Path

from tools.ir_runtime_audit import audit_runtime_file, _bounded_execute
from frontend.quar.ast_nodes import Integer, Variable, BinaryOperation, Assignment, VariableDeclaration, WhileStatement
from frontend.quar.ir.builder import lower_statement
from qrvm.compiler import QRVMCompiler
from qrvm.ir_bridge import compile_ir_statements


class IRRuntimeAuditTests(unittest.TestCase):
    def audit_source(self, source):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'program.vq'
            path.write_text(source, encoding='utf-8')
            return audit_runtime_file(path)

    def test_expected_error_is_only_a_candidate(self):
        from tools.ir_runtime_audit import classify_audit_result
        self.assertEqual(classify_audit_result(Path('225 assertion error.vq'), 'compile_error'),
                         'expected_error_candidate')
        self.assertEqual(classify_audit_result(Path('225 assertion error.vq'), 'bytecode_mismatch'),
                         'regression')

    def test_module_fixtures_are_not_entry_programs(self):
        from tools.ir_runtime_audit import classify_audit_result
        path = Path('examples/typed/XX modules/fixtures/modules48/a.vq')
        self.assertEqual(classify_audit_result(path, 'module_error'), 'module_fixture')

    def test_unexpected_error_is_not_hidden(self):
        from tools.ir_runtime_audit import classify_audit_result
        self.assertEqual(classify_audit_result(Path('ordinary.vq'), 'compile_error'),
                         'unresolved_error')

    def test_explicit_timeout_expectation(self):
        from tools.ir_runtime_audit import classify_audit_result
        path = Path('examples/0.0.3/typed/04 loops/094 infinite while error.vq')
        self.assertEqual(classify_audit_result(path, 'skipped_timeout'),
                         'expected_negative_verified')
        self.assertEqual(classify_audit_result(path, 'runtime_mismatch'), 'regression')

    def test_explicit_module_failure_expectation(self):
        from tools.ir_runtime_audit import classify_audit_result
        path = Path('examples/0.0.3/typed/XX modules/047 missing module.vq')
        self.assertEqual(classify_audit_result(path, 'module_error'),
                         'expected_negative_verified')

    def test_unlisted_timeout_remains_unresolved(self):
        from tools.ir_runtime_audit import classify_audit_result
        self.assertEqual(classify_audit_result(Path('unknown_loop.vq'), 'skipped_timeout'),
                         'unresolved_timeout')

    def test_straight_line_runtime_parity(self):
        status, detail = self.audit_source('int x = 2; int y = x + 3;')
        self.assertEqual(status, 'runtime_equal', detail)

    def test_captured_print_runtime_parity(self):
        status, detail = self.audit_source('print(42);')
        self.assertEqual(status, 'runtime_equal', detail)

    def test_console_operations_are_allowed_in_isolated_worker(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _program_safe
        self.assertTrue(_program_safe({'instructions': [
            (OpCode.CONSOLE_QUERY, 'Console.arg_count'),
            (OpCode.POP, None),
            (OpCode.PUSH_STRING, 'hello'),
            (OpCode.CONSOLE_WRITE, 'stdout'),
        ]}))

    def test_console_environment_is_deterministic(self):
        from qrvm.instructions import OpCode
        program = QRVMCompiler().compile([])
        program['instructions'] = [
            (OpCode.PUSH_STRING, 'QUAR_AUDIT_SECRET'),
            (OpCode.CONSOLE_QUERY, 'Console.env_exists'),
            (OpCode.HALT, None),
        ]
        status, result = _bounded_execute(program)
        self.assertEqual(status, 'ok')
        self.assertEqual(result[2], [False])

    def test_panic_and_exit_are_isolated_and_comparable(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _program_safe
        for opcode, value in ((OpCode.PANIC, 'fatal'), (OpCode.EXIT, 0)):
            program = QRVMCompiler().compile([])
            program['instructions'] = [
                (OpCode.PUSH_STRING if isinstance(value, str) else OpCode.PUSH_INT, value),
                (opcode, None),
            ]
            self.assertTrue(_program_safe(program))
            status, result = _bounded_execute(program)
            self.assertEqual(status, 'ok')
            self.assertEqual(result[0][0], 'error')
            self.assertEqual(result[0][1], 'QuarPanic' if opcode == OpCode.PANIC else 'QuarExit')

    def test_panic_and_exit_source_parity(self):
        for source in ('panic("fatal");', 'exit(0);'):
            with self.subTest(source=source):
                status, detail = self.audit_source(source)
                self.assertEqual(status, 'runtime_equal', detail)

    def test_input_uses_deterministic_eof(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _program_safe
        program = QRVMCompiler().compile([])
        program['instructions'] = [(OpCode.INPUT, False), (OpCode.HALT, None)]
        self.assertTrue(_program_safe(program))
        status, result = _bounded_execute(program)
        self.assertEqual(status, 'ok')
        self.assertEqual(result[0][0], 'error')
        self.assertEqual(result[0][1], 'RuntimeError')
        self.assertIn('EOF', result[0][2])

    def test_input_source_parity_with_empty_stdin(self):
        status, detail = self.audit_source('string name = input();')
        self.assertEqual(status, 'runtime_equal', detail)

    def test_pure_path_and_bytes_operations_are_allowed(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _instructions_safe
        for operation in ('Bytes.from_hex', 'Bytes.to_hex', 'Bytes.length',
                          'Path.join', 'Path.name', 'Path.parent', 'Path.stem', 'Path.suffix'):
            self.assertTrue(_instructions_safe([(OpCode.FILE_OP, (operation, 1))]))
        self.assertFalse(_instructions_safe([(OpCode.FILE_OP, ('File.write_text', 2))]))

    def test_pure_path_source_parity(self):
        status, detail = self.audit_source('print(Path.name(Path.join("alpha", "beta.txt")));')
        self.assertEqual(status, 'runtime_equal', detail)

    def test_file_access_remains_excluded(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _program_safe
        self.assertFalse(_program_safe({'instructions': [(OpCode.FILE_OP, ('read', 1))]}))

    def test_unsafe_opcodes_include_nested_file_operations(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import unsafe_program_opcodes
        program = {'instructions': [(OpCode.TRY_CATCH, (
            [(OpCode.FILE_OP, ('read', 1))], 'err', [(OpCode.INPUT, None)]))],
            'functions': {'f': {'instructions': [(OpCode.CONSOLE_WRITE, None)]}}}
        self.assertEqual(unsafe_program_opcodes(program),
                         ('FILE_OP',))

    def test_effectful_audit_explains_excluded_opcode(self):
        status, detail = self.audit_source('print(42);')
        self.assertEqual(status, 'runtime_equal', detail)
        from tools.ir_runtime_audit import unsafe_program_opcodes
        from qrvm.instructions import OpCode
        self.assertEqual(unsafe_program_opcodes(
            {'instructions': [(OpCode.FILE_OP, None)]}), ('FILE_OP',))

    def test_match_variant_is_safe(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _instructions_safe
        self.assertTrue(_instructions_safe([(OpCode.MATCH_VARIANT, ('Some', (), 3))]))

    def test_nested_file_operation_is_rejected(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _instructions_safe
        nested = [(OpCode.TRY_CATCH, (
            [(OpCode.FILE_OP, ('read', 1))], 'err', [(OpCode.PRINT, None)]))]
        self.assertFalse(_instructions_safe(nested))

    def test_pure_try_catch_is_safe(self):
        from qrvm.instructions import OpCode
        from tools.ir_runtime_audit import _instructions_safe
        nested = [(OpCode.TRY_CATCH, (
            [(OpCode.PUSH_STRING, 'error'), (OpCode.THROW, False)],
            'err', [(OpCode.PUSH_INT, 42)]))]
        self.assertTrue(_instructions_safe(nested))

    def test_bounded_loop_runtime_parity(self):
        statements = [VariableDeclaration('int', 'counter', Integer(0)),
            WhileStatement(BinaryOperation(Variable('counter'), '<', Integer(3)), [
                Assignment('counter', BinaryOperation(Variable('counter'), '+', Integer(1)))])]
        direct = QRVMCompiler().compile(statements)
        via_ir = compile_ir_statements(tuple(lower_statement(node) for node in statements))
        left_status, left = _bounded_execute(direct)
        right_status, right = _bounded_execute(via_ir)
        self.assertEqual((left_status, right_status), ('ok', 'ok'))
        self.assertEqual(left, right)
        self.assertEqual(left[1]['counter'], 3)

    def test_infinite_loop_times_out(self):
        from unittest.mock import patch
        from frontend.quar.ast_nodes import LoopStatement
        program = QRVMCompiler().compile([LoopStatement([])])
        with patch('tools.ir_runtime_audit.RUNTIME_TIMEOUT_SECONDS', 0.05):
            status, result = _bounded_execute(program)
        self.assertEqual(status, 'timeout')


if __name__ == '__main__':
    unittest.main()
