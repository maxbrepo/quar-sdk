"""Run the Visual Quar ABI/FFI cycle A release validation gates.

Execute from the Quar SDK repository root. Requires a locally installed SDL3.
Returns zero only if every mandatory suite succeeds.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SUITES: tuple[tuple[str, str], ...] = (
    ("Chapter 41 QIR/native calls", "test_ch41_*.py"),
    ("Chapter 42 native types", "test_ch42_*.py"),
    ("Chapter 43 resource lifetime", "test_ch43_cycle_a_*.py"),
    ("QGF cstring return regression", "test_qgf_cstring_return_hotfix.py"),
    ("Required real SDL3 lifecycle", "test_ch43_real_sdl3_required.py"),
)


def main() -> int:
    """Run all mandatory gates and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, default=Path.cwd(), help="Quar SDK root directory")
    args = parser.parse_args()
    root = args.sdk.resolve()
    tests = root / "tests"
    if not tests.is_dir():
        parser.error(f"SDK tests directory not found: {tests}")

    failures: list[str] = []
    for label, pattern in SUITES:
        if not list(tests.glob(pattern)):
            print(f"FAIL: {label}: no matching tests ({pattern})", flush=True)
            failures.append(label)
            continue
        print(f"\n=== {label} ===", flush=True)
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"],
            cwd=root,
            check=False,
        )
        if result.returncode:
            failures.append(label)

    print("\n=== Cycle A release gate summary ===", flush=True)
    for label, _ in SUITES:
        print(f"{'FAIL' if label in failures else 'PASS'}: {label}")
    print("QGF application tests: NOT RUN (external repository)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
