"""Executable parity tests for Unicode scalar iteration with loop transfers."""
import unittest

from frontend.quar.ast_nodes import (Assignment, BinaryOperation, BreakStatement,
    ContinueStatement, FunctionCall, IfStatement, Integer, ReturnStatement,
    String, Variable, VariableDeclaration, WhileStatement)
from test_ch17_66_qir_array_source_integration import SourceArrayIntegrationTests


def v(name):
    return Variable(name)


def b(left, op, right):
    return BinaryOperation(left, op, right)


def intrinsic(name, *args):
    return FunctionCall(name, list(args))


class UnicodeLoopTransfersTests(unittest.TestCase):
    run_both = SourceArrayIntegrationTests.run_both

    def program(self, text, transfers):
        return [
            VariableDeclaration('string', 'text', String(text)),
            VariableDeclaration('i32', 'index', Integer(0)),
            VariableDeclaration('i32', 'total', Integer(0)),
            WhileStatement(b(v('index'), '<', intrinsic('__qir_utf8_scalar_len', v('text'))), [
                Assignment('index', b(v('index'), '+', Integer(1))),
                *transfers,
                Assignment('total', b(v('total'), '+',
                    intrinsic('__qir_utf8_scalar_at', v('text'), b(v('index'), '-', Integer(1))))),
            ]),
            ReturnStatement(v('total')),
        ]

    def test_continue_skips_unicode_scalar(self):
        self.run_both(self.program('aé😀', [
            IfStatement(b(v('index'), '==', Integer(2)), [ContinueStatement()], []),
        ]), ord('a') + ord('😀'))

    def test_break_stops_before_unicode_scalar(self):
        self.run_both(self.program('aé😀', [
            IfStatement(b(v('index'), '==', Integer(3)), [BreakStatement()], []),
        ]), ord('a') + ord('é'))

    def test_empty_text_with_transfers(self):
        self.run_both(self.program('', [
            IfStatement(b(v('index'), '==', Integer(1)), [BreakStatement()], []),
        ]), 0)


if __name__ == '__main__':
    unittest.main()
