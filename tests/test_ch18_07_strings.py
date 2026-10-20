"""Chapter 18.7: Unicode string semantics and VM compatibility."""
import unittest
from qrvm.string_ops import StringOperationError, string_length, string_operation
from qrvm.instructions import OpCode as O
from qrvm.vm import QRVM


class StringTests(unittest.TestCase):
    def test_unicode_length(self):
        self.assertEqual(string_length("a🦊é"), 3)

    def test_unicode_substring(self):
        self.assertEqual(string_operation("substring", ["a🦊é", 1, 1]), "🦊")

    def test_end_empty_slice(self):
        self.assertEqual(string_operation("substring", ["abc", 3, 0]), "")

    def test_negative_range(self):
        with self.assertRaisesRegex(StringOperationError, "out of bounds"):
            string_operation("substring", ["abc", -1, 1])

    def test_bool_index_rejected(self):
        with self.assertRaisesRegex(StringOperationError, "integer"):
            string_operation("substring", ["abc", True, 1])

    def test_find_and_replace(self):
        self.assertEqual(string_operation("find", ["a🦊b", "🦊"]), 1)
        self.assertEqual(string_operation("replace", ["aba", "a", "x"]), "xbx")

    def test_trim_and_conversion(self):
        self.assertEqual(string_operation("trim", ["  hi  "]), "hi")
        self.assertEqual(string_operation("to_string", [False]), "false")
        self.assertEqual(string_operation("to_int", ["42"]), 42)
        self.assertEqual(string_operation("to_double", ["1.5"]), 1.5)

    def test_wrong_arity(self):
        with self.assertRaisesRegex(StringOperationError, "requires 3"):
            string_operation("substring", ["abc"])

    def test_invalid_conversion(self):
        with self.assertRaisesRegex(StringOperationError, "conversion failed"):
            string_operation("to_int", ["nope"])

    def test_vm_length_and_substring(self):
        vm = QRVM()
        vm.run([(O.PUSH_STRING, "a🦊é"), (O.STORE, "s"), (O.LENGTH, "s"),
                (O.PUSH_STRING, "a🦊é"), (O.PUSH_INT, 1), (O.PUSH_INT, 1),
                (O.STRING_OP, ("substring", 3))])
        self.assertEqual(vm.stack, [3, "🦊"])

    def test_vm_bad_index(self):
        vm = QRVM()
        with self.assertRaisesRegex(StringOperationError, "integer"):
            vm.run([(O.PUSH_STRING, "abc"), (O.PUSH_INT, True),
                    (O.PUSH_INT, 1), (O.STRING_OP, ("substring", 3))])


if __name__ == "__main__":
    unittest.main()
