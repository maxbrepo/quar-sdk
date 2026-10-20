"""Chapter 18.8: struct layout and field access compatibility."""
import unittest
from qrvm.struct_access import StructAccessError, create_struct, load_field, store_field
from qrvm.instructions import OpCode as O
from qrvm.vm import QRVM


class StructTests(unittest.TestCase):
    def test_create_preserves_field_order(self):
        obj = create_struct("Point", ("x", "y"), (3, 4))
        self.assertEqual(list(obj["__fields__"]), ["x", "y"])

    def test_rejects_duplicate_fields(self):
        with self.assertRaisesRegex(StructAccessError, "Duplicate"):
            create_struct("P", ("x", "x"), (1, 2))

    def test_rejects_missing_values(self):
        with self.assertRaisesRegex(StructAccessError, "count"):
            create_struct("P", ("x",), ())

    def test_rejects_invalid_type_name(self):
        with self.assertRaises(StructAccessError):
            create_struct("", (), ())

    def test_rejects_invalid_field_name(self):
        with self.assertRaises(StructAccessError):
            create_struct("P", ("",), (1,))

    def test_load_and_store_shared_identity(self):
        obj = create_struct("P", ("x",), (1,))
        variables = {"a": obj, "b": obj}
        store_field(variables, "a", "x", 9)
        self.assertEqual(load_field(variables, "b", "x"), 9)

    def test_unknown_member(self):
        with self.assertRaisesRegex(StructAccessError, "Unknown field"):
            load_field({"a": create_struct("P", ("x",), (1,))}, "a", "y")

    def test_vm_create_read_write(self):
        vm = QRVM()
        vm.run([(O.PUSH_INT, 1), (O.PUSH_INT, 2),
                (O.OBJECT_NEW, ("p", "Point", ("x", "y"))),
                (O.PUSH_INT, 7), (O.MEMBER_STORE, ("p", "x")),
                (O.MEMBER_LOAD, ("p", "x"))])
        self.assertEqual(vm.stack, [7])
        self.assertEqual(vm.heap.object_count, 1)

    def test_vm_rejects_duplicate_without_consuming_stack(self):
        vm = QRVM()
        with self.assertRaisesRegex(StructAccessError, "Duplicate"):
            vm.run([(O.PUSH_INT, 1), (O.PUSH_INT, 2),
                    (O.OBJECT_NEW, ("p", "P", ("x", "x")))])
        self.assertEqual(vm.stack, [1, 2])

    def test_vm_bad_member_store_preserves_value(self):
        vm = QRVM()
        with self.assertRaisesRegex(StructAccessError, "Unknown field"):
            vm.run([(O.PUSH_INT, 1), (O.OBJECT_NEW, ("p", "P", ("x",))),
                    (O.PUSH_INT, 9), (O.MEMBER_STORE, ("p", "y"))])
        self.assertEqual(vm.stack, [9])


if __name__ == "__main__":
    unittest.main()
