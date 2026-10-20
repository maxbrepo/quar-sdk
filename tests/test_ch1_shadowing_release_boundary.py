"""Guard the release boundary while lexical shadowing is opt-in."""
import unittest
from pathlib import Path

from main import build_frontend, collect_batch_sources
from tests.test_ch1_c_while_lexical import CWhileLexicalTests


class ShadowingReleaseBoundaryTests(unittest.TestCase):
    def test_experimental_sources_are_outside_official_examples(self):
        root = Path(__file__).resolve().parents[1]
        examples = (root / "examples").resolve()
        fixtures = (root / "tests" / "fixtures" / "ch1_lexical_experimental").resolve()
        self.assertTrue(fixtures.is_dir())
        sources = collect_batch_sources(examples)
        self.assertGreaterEqual(len(sources), 247)
        self.assertTrue(all(examples in source.resolve().parents for source in sources))
        self.assertFalse(any(fixtures in source.resolve().parents for source in sources))

    def test_shadowing_remains_opt_in_for_all_profiles(self):
        root = Path(__file__).resolve().parents[1]
        for profile in ("typed", "inferred", "mixed"):
            source = (root / "tests" / "fixtures" / "ch1_lexical_experimental" /
                      profile / "ch1 while lexical parity.vq").read_text(encoding="utf-8")
            with self.subTest(profile=profile):
                if profile in ("typed", "mixed"):
                    with self.assertRaises(Exception):
                        build_frontend(source)
                else:
                    build_frontend(source)
                build_frontend(source, lexical=True)

    def test_while_shadowing_and_outer_update_in_same_loop(self):
        CWhileLexicalTests.check_source(
            self,
            "int counter = 0; int value = 5; int result = 0; "
            "while (counter < 2) { "
            "int value = 9; result = result + value; "
            "counter = counter + 1; print(value); } "
            "print(value); print(result);",
            ["9", "9", "5", "18"],
        )


if __name__ == "__main__":
    unittest.main()
