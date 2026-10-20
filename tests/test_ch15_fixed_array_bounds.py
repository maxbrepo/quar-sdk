"""Chapter 15.2: static bounds checking for fixed-size arrays."""
import unittest
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.errors import SemanticError


def check(source):
    """Parse and analyze a source snippet; return None on success."""
    program = Parser(Lexer(source).tokenize()).parse()
    SemanticAnalyzer().analyze(program)


class FixedArrayBoundsTests(unittest.TestCase):
    def test_valid_read(self):
        check('i32 a[2] = {10, 20}; print(a[1]);')

    def test_valid_write(self):
        check('i32 a[2] = {10, 20}; a[0] = 30;')

    def test_read_upper_bound(self):
        with self.assertRaisesRegex(SemanticError, 'out of bounds'):
            check('i32 a[2] = {10, 20}; print(a[2]);')

    def test_write_upper_bound(self):
        with self.assertRaisesRegex(SemanticError, 'out of bounds'):
            check('i32 a[2] = {10, 20}; a[2] = 30;')

    def test_negative_index(self):
        with self.assertRaisesRegex(SemanticError, 'out of bounds'):
            check('i32 a[2] = {10, 20}; print(a[-1]);')

    def test_matrix_second_dimension(self):
        with self.assertRaisesRegex(SemanticError, 'dimension 2'):
            check('i32 a[2][3] = {1,2,3,4,5,6}; print(a[1][3]);')

    def test_matrix_first_dimension(self):
        with self.assertRaisesRegex(SemanticError, 'dimension 1'):
            check('i32 a[2][3] = {1,2,3,4,5,6}; print(a[2][1]);')

    def test_variable_index_is_not_statically_rejected(self):
        check('i32 a[2] = {10, 20}; i32 i = 1; print(a[i]);')


if __name__ == '__main__':
    unittest.main()
