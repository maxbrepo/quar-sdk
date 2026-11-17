"""QIR-01 coverage checks on the existing Cycle 4 QRVM baseline."""
from __future__ import annotations

import unittest
from pathlib import Path

from tools.qir_cycle5_coverage import CHAPTER_SAMPLES, PROFILES, audit

ROOT = Path(__file__).resolve().parents[1]


class QIR01CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit(ROOT)

    def test_all_curated_sources_run_on_qrvm(self):
        self.assertEqual(len(self.report["samples"]), len(CHAPTER_SAMPLES) * len(PROFILES))
        self.assertTrue(all(item["qrvm"] == "passed" for item in self.report["samples"]))

    def test_profile_output_parity_for_every_chapter(self):
        self.assertTrue(all(item["qrvm_output_parity"] for item in self.report["chapter_comparisons"]))

    def test_lowering_reports_gaps_explicitly(self):
        functions = [f for item in self.report["samples"] for f in item["functions"]]
        self.assertTrue(any(f["qir"] == "lowered" for f in functions))
        self.assertTrue(any(f["qir"] == "unsupported" for f in functions))
        self.assertTrue(all(f.get("reason") for f in functions if f["qir"] == "unsupported"))

    def test_source_paths_and_hashes_are_recorded(self):
        for item in self.report["samples"]:
            self.assertTrue((ROOT / item["source"]).is_file())
            self.assertEqual(len(item["sha256"]), 64)
            self.assertEqual(item["profile"] in PROFILES, True)

    def test_no_claim_of_qir_execution(self):
        self.assertIn("not QIR execution", self.report["scope"])


if __name__ == "__main__":
    unittest.main()
