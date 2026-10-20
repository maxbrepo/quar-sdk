"""Chapter 18.6: array access, shape and heap compatibility."""
import unittest
from qrvm.array_access import ArrayAccessError, resolve_index, validate_shape
from qrvm.instructions import OpCode as O
from qrvm.vm import QRVM


class ArrayTests(unittest.TestCase):
    def test_one_dimensional_index(self):
        self.assertEqual(resolve_index({"__array__": [4, 5]}, 1), 1)

    def test_two_dimensional_index(self):
        self.assertEqual(resolve_index({"__array__": [0] * 6, "__second_size__": 3}, 1, 2, two_dimensional=True), 5)

    def test_bool_index_rejected(self):
        with self.assertRaisesRegex(ArrayAccessError, "int"):
            resolve_index({"__array__": [4]}, True)

    def test_negative_index_rejected(self):
        with self.assertRaisesRegex(ArrayAccessError, "out of bounds"):
            resolve_index({"__array__": [4]}, -1)

    def test_multidimensional_bounds(self):
        obj = {"__array__": [0] * 6, "__second_size__": 3}
        with self.assertRaisesRegex(ArrayAccessError, "out of bounds"):
            resolve_index(obj, 2, 0, two_dimensional=True)

    def test_zero_width_rejected(self):
        with self.assertRaisesRegex(ArrayAccessError, "positive"):
            validate_shape(0, 0)

    def test_inconsistent_shape_rejected(self):
        with self.assertRaisesRegex(ArrayAccessError, "divisible"):
            validate_shape(5, 2)

    def test_vm_roundtrip(self):
        vm = QRVM()
        vm.run([(O.ARRAY_NEW, ("a", 2, 0, 0, None)), (O.PUSH_INT, 0),
                (O.PUSH_INT, 42), (O.ARRAY_STORE, ("a", False)),
                (O.PUSH_INT, 0), (O.ARRAY_LOAD, ("a", False))])
        self.assertEqual(vm.stack[-1], 42)
        self.assertIs(vm.heap.get(1).value, vm.variables["a"])

    def test_vm_rejects_bad_shape(self):
        vm = QRVM()
        with self.assertRaisesRegex(ArrayAccessError, "positive"):
            vm.run([(O.ARRAY_NEW, ("a", 0, 0, 0, 0))])

    def test_vm_two_dimensional_roundtrip(self):
        vm = QRVM()
        vm.run([(O.ARRAY_NEW, ("m", 6, 0, 0, 3)),
                (O.PUSH_INT, 1), (O.PUSH_INT, 2), (O.PUSH_INT, 77),
                (O.ARRAY_STORE, ("m", True)),
                (O.PUSH_INT, 1), (O.PUSH_INT, 2), (O.ARRAY_LOAD, ("m", True))])
        self.assertEqual(vm.stack[-1], 77)


if __name__ == "__main__":
    unittest.main()
