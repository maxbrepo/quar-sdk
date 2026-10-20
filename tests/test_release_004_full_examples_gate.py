"""Release 0.0.4 gate: execute every non-interactive example with QRVM."""
import unittest
from collections import Counter
from pathlib import Path

from main import collect_batch_sources, execute_regression_source


class Release004FullExamplesGate(unittest.TestCase):
    def test_all_discovered_examples_have_expected_results(self):
        root = Path(__file__).resolve().parents[1] / "examples"
        sources = collect_batch_sources(root)
        self.assertGreaterEqual(len(sources), 247, "Example discovery unexpectedly shrank")
        outcomes = Counter()
        failures = []
        for source in sources:
            with self.subTest(source=str(source.relative_to(root))):
                try:
                    status, detail = execute_regression_source(source)
                except Exception as error:
                    status, detail = "CRASH", repr(error)
                outcomes[status] += 1
                if status not in {"PASS", "EXPECTED ERROR"}:
                    failures.append(f"{source.relative_to(root)}: {status}: {detail}")
        self.assertFalse(failures, "\n".join(failures))
        self.assertGreater(outcomes["PASS"], 0)
        self.assertGreater(outcomes["EXPECTED ERROR"], 0)
