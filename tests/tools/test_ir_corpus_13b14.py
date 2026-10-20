"""Corpus-based IR parity checks, without claiming runtime equivalence."""
import unittest
from pathlib import Path

from frontend.quar.ir.builder import lower_statement
from frontend.quar.ast_nodes import ReturnStatement
from qrvm.ir_bridge import to_ast
from tools.ir_corpus_audit import audit_file


class IRCorpusTests(unittest.TestCase):
    def test_void_return_roundtrip(self):
        original = ReturnStatement(None)
        self.assertEqual(to_ast(lower_statement(original)), original)

    def test_existing_void_function_examples(self):
        root = Path(__file__).resolve().parents[2]
        for filename in ('023 void functions.vq', '099 void function.vq'):
            matches = list((root / 'examples').rglob(filename))
            self.assertEqual(len(matches), 1)
            status, detail = audit_file(matches[0])
            self.assertEqual(status, 'bytecode_equal', detail)


if __name__ == '__main__':
    unittest.main()
