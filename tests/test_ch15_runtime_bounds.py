"""Chapter 15.3: runtime sequence bounds and index-type regression tests."""
import unittest
from qrvm.instructions import OpCode
from qrvm.vm import QRVM


class RuntimeBoundsTests(unittest.TestCase):
    def run_load(self, value, index):
        vm = QRVM()
        vm.variables = {"item": value}
        vm.stack = [index]
        vm.execute([(OpCode.ARRAY_LOAD, ("item", False))], vm.variables)
        return vm.stack[-1]

    def run_store(self, index):
        vm = QRVM()
        vm.variables = {"item": {"__array__": [10, 20], "__second_size__": None, "__dynamic__": False}}
        vm.stack = [index, 30]
        vm.execute([(OpCode.ARRAY_STORE, ("item", False))], vm.variables)
        return vm.variables["item"]["__array__"]

    def test_array_valid_store(self):
        self.assertEqual(self.run_store(1), [10, 30])

    def test_array_store_invalid_type(self):
        for index in (1.0, True, "1", None):
            with self.subTest(index=index), self.assertRaisesRegex(RuntimeError, "Array index must be int"):
                self.run_store(index)

    def test_array_store_out_of_bounds(self):
        for index in (-1, 2):
            with self.subTest(index=index), self.assertRaisesRegex(RuntimeError, "out of bounds"):
                self.run_store(index)

    def test_string_load_valid(self):
        self.assertEqual(self.run_load("ab", 1), "b")

    def test_string_load_invalid_type(self):
        for index in (1.0, True, "1", None):
            with self.subTest(index=index), self.assertRaisesRegex(RuntimeError, "String index must be int"):
                self.run_load("ab", index)

    def test_string_load_out_of_bounds(self):
        for index in (-1, 2):
            with self.subTest(index=index), self.assertRaisesRegex(RuntimeError, "out of bounds"):
                self.run_load("ab", index)

    def test_bytes_load_invalid_type(self):
        with self.assertRaisesRegex(RuntimeError, "Bytes index must be int"):
            self.run_load(b"ab", True)

    def test_array_load_invalid_type(self):
        with self.assertRaisesRegex(RuntimeError, "Array index must be int"):
            self.run_load({"__array__": [1], "__second_size__": None}, True)


if __name__ == "__main__":
    unittest.main()
