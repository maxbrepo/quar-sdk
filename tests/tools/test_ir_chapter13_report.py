"""Chapter 13B parity report classification regression tests."""
import unittest
from collections import Counter
from tools.ir_chapter13_report import render_report, KNOWN_LIMITATIONS


class IRChapter13ReportTests(unittest.TestCase):
    def test_equal_compile_failure_is_not_reported_as_runtime_success(self):
        report = render_report(1, Counter({'compile_error_equal': 1}),
                               [('103 named arguments.vq', 'named_arguments_not_compiled', 'compile_error_equal')], [])
        self.assertIn('not** that rejection was correct', report)
        self.assertIn('named_arguments_not_compiled', report)
        self.assertNotIn('`runtime_equal` | 1', report)

    def test_ir_regressions_remain_visible(self):
        report = render_report(1, Counter({'compile_error_mismatch': 1}), [],
                               [('broken.vq', 'compile_error_mismatch', 'different')])
        self.assertIn('regressions: **1**', report)

    def test_known_valid_named_argument_examples_are_blockers(self):
        self.assertEqual(KNOWN_LIMITATIONS['103 named arguments.vq'], 'named_arguments_not_compiled')
        self.assertEqual(KNOWN_LIMITATIONS['104 positional and named arguments.vq'], 'named_arguments_not_compiled')


if __name__ == '__main__':
    unittest.main()
