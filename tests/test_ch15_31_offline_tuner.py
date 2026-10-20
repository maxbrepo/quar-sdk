"""Chapter 15.31: opt-in offline tuner A smoke tests."""
import unittest
from qrvm.offline_tuner import compare_variants


class OfflineTunerTests(unittest.TestCase):
    def test_measurement(self):
        result = compare_variants({'one': lambda: sum(range(10))}, repeats=3)
        self.assertEqual(result[0].name, 'one')
        self.assertEqual(len(result[0].samples_ns), 3)
        self.assertTrue(all(sample >= 0 for sample in result[0].samples_ns))

    def test_multiple_variants(self):
        result = compare_variants({'one': lambda: 1, 'two': lambda: 2})
        self.assertEqual({r.name for r in result}, {'one', 'two'})

    def test_empty(self):
        with self.assertRaises(ValueError):
            compare_variants({})

    def test_invalid_repeats(self):
        with self.assertRaises(ValueError):
            compare_variants({'x': lambda: None}, 0)

    def test_noncallable(self):
        with self.assertRaises(ValueError):
            compare_variants({'x': 3})

    def test_propagate_failure(self):
        def fail():
            raise RuntimeError('benchmark failed')
        with self.assertRaises(RuntimeError):
            compare_variants({'fail': fail})


if __name__ == '__main__':
    unittest.main()
