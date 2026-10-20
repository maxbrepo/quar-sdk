"""Portable QBC serialization and cache tests."""
import tempfile
import unittest
from pathlib import Path

from qrvm.bytecode_format import wrap_legacy_program
from qrvm.bytecode_loader import run_loaded_bytecode
from qrvm.bytecode_serialization import QBCError, dumps_qbc, loads_qbc, read_qbc, write_qbc
from qrvm.bytecode_cache import cache_key, cache_path
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class QBCSerializationTests(unittest.TestCase):
    def sample(self):
        return wrap_legacy_program([(OpCode.PUSH_INT, 12), (OpCode.HALT, None)])

    def test_roundtrip(self):
        loaded = loads_qbc(dumps_qbc(self.sample()))
        self.assertEqual(loaded.package, self.sample())

    def test_deterministic(self):
        self.assertEqual(dumps_qbc(self.sample()), dumps_qbc(self.sample()))

    def test_execute(self):
        vm = QRVM()
        run_loaded_bytecode(vm, loads_qbc(dumps_qbc(self.sample())))
        self.assertEqual(vm.stack, [12])

    def test_unicode_and_float(self):
        p = wrap_legacy_program([(OpCode.PUSH_STRING, 'caffè 🦊'),
                                 (OpCode.PUSH_DOUBLE, 2.5), (OpCode.HALT, None)])
        self.assertEqual(loads_qbc(dumps_qbc(p)).package, p)

    def test_function_and_tuple_key(self):
        p = self.sample()
        p['class_methods'] = {('Box', 'get'): {
            'parameters': [], 'return_type': 'int',
            'instructions': [(OpCode.PUSH_INT, 3), (OpCode.RETURN, None)]}}
        self.assertEqual(loads_qbc(dumps_qbc(p)).package, p)

    def test_checksum_rejects_corruption(self):
        blob = bytearray(dumps_qbc(self.sample()))
        blob[-1] ^= 1
        with self.assertRaises(QBCError):
            loads_qbc(bytes(blob))

    def test_rejects_truncated(self):
        with self.assertRaises(QBCError):
            loads_qbc(dumps_qbc(self.sample())[:-1])

    def test_rejects_version(self):
        blob = bytearray(dumps_qbc(self.sample()))
        blob[4] = 99
        with self.assertRaises(QBCError):
            loads_qbc(bytes(blob))

    def test_rejects_python_object(self):
        p = self.sample()
        p['bad'] = object()
        with self.assertRaises(QBCError):
            dumps_qbc(p)

    def test_disk_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.qbc'
            write_qbc(path, self.sample())
            self.assertEqual(read_qbc(path).package, self.sample())

    def test_cache_invalidation(self):
        a = cache_key(b'source', compiler_id='quarc-0.0.4', dependencies={'lib': b'a'})
        b = cache_key(b'source', compiler_id='quarc-0.0.4', dependencies={'lib': b'b'})
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, cache_key(b'changed', compiler_id='quarc-0.0.4', dependencies={'lib': b'a'}))
        self.assertTrue(str(cache_path('/tmp/cache', a)).endswith('.qbc'))

    def test_cache_key_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            cache_path('/tmp/cache', '../unsafe')


if __name__ == '__main__':
    unittest.main()
