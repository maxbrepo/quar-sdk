"""Ensure lexical CLI switches are opt-in and passed to both execution paths."""
import unittest
from unittest.mock import patch
import main as entry


class LexicalCLIActivationTests(unittest.TestCase):
    def test_switches(self):
        self.assertEqual(entry.parse_lexical_options(['-f', 'demo.vq']), (['-f', 'demo.vq'], False, False))
        self.assertEqual(entry.parse_lexical_options(['-f', 'demo.vq', '--lexical', '--lexical-inference']), (['-f', 'demo.vq'], True, True))
        with self.assertRaises(ValueError):
            entry.parse_lexical_options(['--lexical-inference'])

    def test_reject_duplicate_lexical_switches(self):
        with self.assertRaisesRegex(ValueError, "--lexical may be specified only once"):
            entry.parse_lexical_options(['--lexical', '--lexical'])
        with self.assertRaisesRegex(ValueError, "--lexical-inference may be specified only once"):
            entry.parse_lexical_options(['--lexical', '--lexical-inference', '--lexical-inference'])

    def test_kart_lexical_combination_is_rejected(self):
        # Kart loads modules through a separate frontend path. Reject the flag
        # rather than silently executing a program without lexical lowering.
        with (patch.object(entry.sys, 'argv', ['quarc', '--kart', '--lexical', '-f', 'demo.vq']),
              patch.object(entry, 'parse_source_argument') as parse_source,
              patch('builtins.print') as output):
            entry.main()
        parse_source.assert_not_called()
        self.assertIn('--lexical is not yet supported with --kart',
                      ' '.join(str(call) for call in output.call_args_list))

    def test_qrvm_route(self):
        with (patch.object(entry, 'parse_source_argument', return_value=('demo.vq', None)),
              patch.object(entry, 'load_source_file', return_value='int x = 1;'),
              patch.object(entry, 'select_execution_mode', return_value='1'),
              patch.object(entry, 'build_frontend', return_value=([], {})) as frontend,
              patch.object(entry, 'run_qrvm') as qrvm,
              patch.object(entry.sys, 'argv', ['quarc', '-f', 'demo.vq', '--lexical'])):
            entry.main()
        self.assertTrue(frontend.call_args.kwargs['lexical'])
        self.assertTrue(qrvm.call_args.kwargs['lexical'])

    def test_c_route(self):
        with (patch.object(entry, 'parse_source_argument', return_value=('demo.vq', None)),
              patch.object(entry, 'load_source_file', return_value='int x = 1;'),
              patch.object(entry, 'select_execution_mode', return_value='2'),
              patch.object(entry, 'build_frontend', return_value=([], {})),
              patch.object(entry, 'detect_host', return_value='linux'),
              patch.object(entry, 'select_target_platform', return_value='linux-x64'),
              patch.object(entry, 'run_compiled') as compiled,
              patch.object(entry.sys, 'argv', ['quarc', '-f', 'demo.vq', '--lexical'])):
            entry.main()
        self.assertTrue(compiled.call_args.kwargs['lexical'])


if __name__ == '__main__':
    unittest.main()
