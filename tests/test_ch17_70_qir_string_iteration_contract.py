"""Validate explicit Unicode scalar traversal independently of source lowering."""
import unittest

from frontend.quar.qir.string_iteration_contract import (
    QStringIterationError, QStringScalar, utf8_scalars,
)


class StringIterationContractTests(unittest.TestCase):
    def test_ascii_offsets(self):
        self.assertEqual(utf8_scalars("ab"), (QStringScalar(97, 0, 1), QStringScalar(98, 1, 2)))

    def test_multibyte_offsets(self):
        self.assertEqual(utf8_scalars("aé😀"), (
            QStringScalar(97, 0, 1), QStringScalar(233, 1, 3),
            QStringScalar(0x1F600, 3, 7),
        ))

    def test_combining_mark_is_separate_scalar(self):
        self.assertEqual(len(utf8_scalars("e\u0301")), 2)

    def test_empty_string(self):
        self.assertEqual(utf8_scalars(""), ())

    def test_surrogate_rejected(self):
        with self.assertRaises(QStringIterationError):
            utf8_scalars("\ud800")

    def test_non_text_rejected(self):
        with self.assertRaises(QStringIterationError):
            utf8_scalars(b"hello")


if __name__ == "__main__":
    unittest.main()
