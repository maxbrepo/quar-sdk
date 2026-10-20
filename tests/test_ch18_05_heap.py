"""Chapter 18.5: bootstrap heap registry and VM compatibility."""
import unittest
from qrvm.heap import BootstrapHeap, HeapError
from qrvm.instructions import OpCode as O
from qrvm.vm import QRVM


class HeapTests(unittest.TestCase):
    def test_register_preserves_identity(self):
        heap = BootstrapHeap()
        value = {"__array__": [1]}
        handle = heap.register("array", value)
        self.assertIs(heap.get(handle).value, value)

    def test_handles_are_distinct(self):
        heap = BootstrapHeap()
        a = heap.register("array", {"__array__": []})
        b = heap.register("array", {"__array__": []})
        self.assertNotEqual(a, b)

    def test_rejects_invalid_objects(self):
        heap = BootstrapHeap()
        with self.assertRaises(HeapError):
            heap.register("array", {})
        with self.assertRaises(HeapError):
            heap.register("object", {"__array__": []})

    def test_invalid_handle(self):
        heap = BootstrapHeap()
        with self.assertRaises(HeapError):
            heap.get(True)

    def test_optional_limit(self):
        heap = BootstrapHeap(max_objects=1)
        heap.register("array", {"__array__": []})
        with self.assertRaisesRegex(HeapError, "limit"):
            heap.register("array", {"__array__": []})

    def test_array_registration(self):
        vm = QRVM()
        vm.run([(O.ARRAY_NEW, ("items", 2, 0, 0, None)), (O.HALT, None)])
        self.assertEqual(vm.heap.snapshot(), ((1, "array"),))
        self.assertIs(vm.heap.get(1).value, vm.variables["items"])

    def test_object_registration(self):
        vm = QRVM()
        vm.run([(O.PUSH_INT, 7), (O.OBJECT_NEW, ("p", "Point", ("x",))), (O.HALT, None)])
        self.assertEqual(vm.heap.snapshot(), ((1, "object"),))
        self.assertEqual(vm.heap.get(1).value["__fields__"]["x"], 7)

    def test_heap_resets_between_runs(self):
        vm = QRVM()
        vm.run([(O.ARRAY_NEW, ("a", 0, 0, 0, None))])
        vm.run([(O.HALT, None)])
        self.assertEqual(vm.heap.object_count, 0)

    def test_aliasing_is_preserved(self):
        vm = QRVM()
        vm.run([(O.ARRAY_NEW, ("a", 1, 0, 0, None)), (O.LOAD, "a"), (O.STORE, "b")])
        self.assertIs(vm.variables["a"], vm.variables["b"])
        self.assertIs(vm.heap.get(1).value, vm.variables["b"])

    def test_snapshot_does_not_expose_payload(self):
        heap = BootstrapHeap()
        heap.register("array", {"__array__": [4]})
        self.assertEqual(heap.snapshot(), ((1, "array"),))


if __name__ == "__main__":
    unittest.main()
