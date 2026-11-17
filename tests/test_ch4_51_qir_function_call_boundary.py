"""Chapter 4.51: characterize public multi-function support and QIR call boundary."""
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.ir.builder import lower_statement
from frontend.quar.qir.ast_lowering import lower_ast_function, QIRASTLoweringError
from frontend.quar.qir.legacy_bridge import lower_ir_function, QIRBridgeError

from test_ch4_49_cli_source_loops import CLISourceLoopTests


class FunctionCallBoundaryTests(unittest.TestCase):
    run_cli_source = CLISourceLoopTests.run_cli_source

    @staticmethod
    def parse(source):
        program = Parser(Lexer(source).tokenize()).parse()
        SemanticAnalyzer().analyze(program)
        return program

    def test_public_cli_nested_function_calls_and_loops(self):
        self.run_cli_source('''
            i32 triangular(i32 limit) {
                i32 index = 0;
                i32 total = 0;
                while (index < limit) {
                    index = index + 1;
                    total = total + index;
                }
                return total;
            }
            i32 combine(i32 first, i32 second) {
                return triangular(first) + triangular(second);
            }
            print(combine(3, 4));
        ''', '16')

    def test_qir_callers_fail_closed_on_both_routes(self):
        program = self.parse('''
            i32 helper(i32 limit) {
                i32 index = 0;
                while (index < limit) { index = index + 1; }
                return index;
            }
            i32 caller(i32 value) { return helper(value); }
        ''')
        self.assertEqual(len(program), 2)
        # Callee bodies and parameter declarations already lower independently.
        lower_ast_function(program[0])
        lower_ir_function(lower_statement(program[0]))
        # Cross-function resolution is not implemented in the QIR adapters.
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(program[1])
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(program[1]))

    def test_qir_rejects_unknown_call_without_silent_fallback(self):
        program = self.parse('''
            i32 helper(i32 value) { return value; }
            i32 caller() { return helper(7); }
        ''')
        with self.assertRaises(QIRASTLoweringError):
            lower_ast_function(program[1])
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(lower_statement(program[1]))


if __name__ == '__main__':
    unittest.main()
