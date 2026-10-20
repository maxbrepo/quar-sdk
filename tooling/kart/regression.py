"""Run the Kart regression suite without modifying the compiler pipeline."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", action="store_true", help="Also run optional C smoke test")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    test_files = sorted((root / "tests").glob("test_kart*.py"))
    if not test_files:
        print("No Kart test files found", file=sys.stderr)
        return 2
    if not args.native:
        test_files = [f for f in test_files if f.name != "test_kart_native_end_to_end.py"]
    print(f"Kart regression: {len(test_files)} test modules", flush=True)
    names = ["tests." + f.stem for f in test_files]
    result = subprocess.run([sys.executable, "-m", "unittest", "-v", *names], cwd=root, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
