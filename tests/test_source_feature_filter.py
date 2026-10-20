"""Regression tests for the terminal source tester feature filter."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vq_main", ROOT / "main.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FeatureFilterTests(unittest.TestCase):
    def test_discovery_and_batch_filter(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "0.0.4" / "typed" / "13 modules"
            second = root / "0.0.4" / "typed" / "12 error handling"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "234 demo.vq").write_text("", encoding="utf-8")
            (second / "220 demo.vq").write_text("", encoding="utf-8")
            self.assertEqual(module.discover_test_features(root), ["12 error handling", "13 modules"])
            sources = module.collect_batch_sources(root)
            selected = module.filter_test_sources(sources, "13 modules")
            self.assertEqual([path.name for path in selected], ["234 demo.vq"])
            self.assertEqual(module.filter_test_sources(sources, None), sources)

    def test_feature_is_exact_directory_match(self):
        source = Path("examples/0.0.4/typed/13 modules/234 demo.vq")
        self.assertTrue(module.source_matches_feature(source, "13 modules"))
        self.assertFalse(module.source_matches_feature(source, "13"))
        self.assertFalse(module.source_matches_feature(source, "14 kart"))


if __name__ == "__main__":
    unittest.main()
