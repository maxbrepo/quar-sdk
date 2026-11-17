"""Test length-delimited UTF-8 storage independently of source lowering."""
import unittest

from frontend.quar.qir.string_iteration_contract import (
    QStringIterationError, QStringScalar, QStringUTF8, decode_utf8, encode_utf8,
)


class StringStorageContractTests(unittest.TestCase):
    def test_roundtrip_multibyte(self):
        storage = encode_utf8("aé😀")
        self.assertEqual(storage.byte_length, 7)
        self.assertEqual(decode_utf8(storage), (
            QStringScalar(97, 0, 1), QStringScalar(233, 1, 3),
            QStringScalar(0x1F600, 3, 7),
        ))

    def test_embedded_nul_is_not_terminator(self):
        self.assertEqual([item.value for item in decode_utf8(encode_utf8("a\0b"))], [97, 0, 98])

    def test_empty_buffer(self):
        self.assertEqual(decode_utf8(encode_utf8("")), ())

    def test_invalid_utf8_rejected(self):
        with self.assertRaises(QStringIterationError):
            decode_utf8(QStringUTF8(b"\xc0\xaf", 2))

    def test_mismatched_length_rejected(self):
        with self.assertRaises(QStringIterationError):
            decode_utf8(QStringUTF8(b"abc", 2))

    def test_surrogate_rejected(self):
        with self.assertRaises(QStringIterationError):
            encode_utf8("\ud800")


if __name__ == "__main__":
    unittest.main()
