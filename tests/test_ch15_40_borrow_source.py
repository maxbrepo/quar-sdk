import tempfile
import unittest
from pathlib import Path
from qrvm.borrow_source import analyze_borrow_source, analyze_borrow_file
from qrvm.ownership_analysis import OwnershipError


class SourceBorrowTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(len(analyze_borrow_source('').statements), 0)

    def test_declaration(self):
        self.assertEqual(len(analyze_borrow_source('int x = 1;').statements), 1)

    def test_read(self):
        analyze_borrow_source('int x = 1; int y = x;')

    def test_assignment(self):
        analyze_borrow_source('int x = 1; x = 2;')

    def test_if(self):
        analyze_borrow_source('int x = 1; if (true) { int y = x; }')

    def test_else(self):
        analyze_borrow_source('int x = 1; if (true) { x = 2; } else { x = 3; }')

    def test_while(self):
        analyze_borrow_source('int x = 1; while (false) { int y = x; }')

    def test_expired_branch(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_source('if (true) { int temp = 1; } int x = temp;')

    def test_expired_loop(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_source('while (false) { int temp = 1; } int x = temp;')

    def test_undefined(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_source('int x = missing;')

    def test_unsupported_print(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_source('print(1);')

    def test_shadowing(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_source('int x = 1; if (true) { int x = 2; }')

    def test_type(self):
        with self.assertRaises(TypeError):
            analyze_borrow_source(None)

    def test_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.vq'
            path.write_text('int x = 1; int y = x;', encoding='utf-8')
            self.assertEqual(len(analyze_borrow_file(path).statements), 2)

    def test_budget(self):
        with self.assertRaises(OwnershipError):
            analyze_borrow_source('int x = 1;', max_facts=1)


if __name__ == '__main__':
    unittest.main()
