"""Run Chapter 10 unit tests and classify historical example outcomes.

Run from repository root: PYTHONPATH=. python tests/ch10/run_acceptance.py
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "0.0.3"
OUTPUT_REFERENCES = Path(__file__).with_name("reference_outputs.json")
KNOWN_BASELINE_FAILURES = {
    "inferred/00 foundation/002 function.vq",
    "mixed/00 foundation/002 function.vq",
    "typed/00 foundation/016 long double.vq",
}


def run_examples():
    references = json.loads(OUTPUT_REFERENCES.read_text(encoding="utf-8"))
    checked_outputs = set()
    counts = {"pass": 0, "expected_error": 0, "module_separate": 0,
              "known_baseline_failure": 0, "unexpected": 0, "output_checked": 0}
    for path in sorted(EXAMPLES.rglob("*.vq")):
        relative = path.relative_to(EXAMPLES)
        if "input" in relative.parts or "fixtures" in relative.parts:
            continue
        if "XX modules" in relative.parts:
            counts["module_separate"] += 1
            continue
        expected_error = " error" in path.stem
        known_failure = relative.as_posix() in KNOWN_BASELINE_FAILURES
        source = path.read_text(encoding="utf-8")
        try:
            tree = Parser(Lexer(source).tokenize()).parse()
            checked = SemanticAnalyzer().analyze(tree)
            program = QRVMCompiler().compile(checked)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                QRVM().run(program)
            if expected_error or known_failure:
                counts["unexpected"] += 1
                print(f"UNEXPECTED SUCCESS: {relative}")
            else:
                name = relative.as_posix()
                reference = references.get(name)
                source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
                if reference is None:
                    counts["unexpected"] += 1
                    print(f"MISSING OUTPUT ORACLE: {relative}")
                elif reference["source_sha256"] != source_digest:
                    counts["unexpected"] += 1
                    print(f"STALE OUTPUT ORACLE: {relative}")
                elif reference["stdout"] != output.getvalue():
                    counts["unexpected"] += 1
                    print(f"OUTPUT MISMATCH: {relative}: "
                          f"expected {reference['stdout']!r}, "
                          f"got {output.getvalue()!r}")
                else:
                    counts["pass"] += 1
                    counts["output_checked"] += 1
                    checked_outputs.add(name)
        except Exception as error:
            if expected_error:
                counts["expected_error"] += 1
            elif known_failure:
                counts["known_baseline_failure"] += 1
            else:
                counts["unexpected"] += 1
                print(f"UNEXPECTED ERROR: {relative}: {type(error).__name__}: {error}")
    unused_references = set(references) - checked_outputs
    for name in sorted(unused_references):
        counts["unexpected"] += 1
        print(f"UNVERIFIED OUTPUT ORACLE: {name}")
    return counts


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests" / "ch10"), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    counts = run_examples()
    print("Example classification:", counts)
    print("Output checks use baseline 0.0.3 references and the 09A specification.")
    print("Note: module tests require the separate module-loader test path.")
    if not result.wasSuccessful() or counts["unexpected"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
