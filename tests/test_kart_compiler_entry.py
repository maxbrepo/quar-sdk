"""Chapter 14.14: opt-in compiler entry point for Kart-installed modules."""
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class KartCompilerEntryTests(unittest.TestCase):
    def test_kart_option_routes_to_module_loader(self):
        source = Path('/tmp/example/main.vq')
        with patch.object(main, 'parse_source_argument', return_value=(source, main.CANONICAL_PROFILE)) as parse, \
             patch.object(main, 'load_source_file', return_value=''), \
             patch.object(main, 'select_execution_mode', return_value='1'), \
             patch.object(main, 'ModuleLoader') as loader, \
             patch.object(main, 'SemanticAnalyzer') as semantic, \
             patch.object(main, 'run_qrvm'), \
             patch.object(main.sys, 'argv', ['main.py', '-f', str(source), '--kart']):
            loader.return_value.load.return_value = []
            semantic.return_value.analyze.return_value = []
            main.main()
            parse.assert_called_once_with(['-f', str(source)])
            loader.assert_called_once_with(source.parent, kart_project=source.parent)
            loader.return_value.load.assert_called_once_with(source)

    def test_legacy_path_does_not_invoke_loader(self):
        source = Path('/tmp/example/main.vq')
        with patch.object(main, 'parse_source_argument', return_value=(source, main.CANONICAL_PROFILE)), \
             patch.object(main, 'load_source_file', return_value=''), \
             patch.object(main, 'select_execution_mode', return_value='1'), \
             patch.object(main, 'ModuleLoader') as loader, \
             patch.object(main, 'build_frontend', return_value=([], {})) as frontend, \
             patch.object(main, 'run_qrvm'), \
             patch.object(main.sys, 'argv', ['main.py', '-f', str(source)]):
            main.main()
            loader.assert_not_called()
            frontend.assert_called_once()
