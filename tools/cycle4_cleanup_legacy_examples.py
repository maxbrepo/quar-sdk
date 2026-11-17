"""Remove only checkpoint-03 examples mistakenly placed in 0.0.4.

Safe to run multiple times. Original 0.0.4 examples are never touched.
"""

import hashlib
from pathlib import Path

SDK_ROOT = Path(__file__).resolve().parents[1]
MOVED_FILES = [['examples/0.0.4/typed/01 primitives/ch1 function and local values.vq', '5fd224385d61a4bf01ea397d7628105b45b3eea5a9d50f3fe618fc70b779eb52'], ['examples/0.0.4/typed/01 primitives/ch1 nested scope baseline.vq', 'eb1403b8533db88159aa859e0e3848d517ab7bd41343435017e66b206d9c0042'], ['examples/0.0.4/typed/01 primitives/ch1 forward and mutual functions.vq', '4b7f8d9807619dc15af5e40c3910c1fc1c100b3945a3f5c2209532c503f9332b'], ['examples/0.0.4/inferred/01 primitives/ch1 forward and mutual functions.vq', '21e10c11f8b4e5fd39d7a33c11d4b15837d2be045715c24a7635caa0f37ec157'], ['examples/0.0.4/mixed/01 primitives/ch1 forward and mutual functions.vq', 'eb667a367d0bd3e5612d1d89bcce77eba01daac74862db9a0e1555b2347fe3b4']]


def clean(root: Path = SDK_ROOT) -> tuple[int, int]:
    """Delete known misplaced files; return (removed_count, already_absent_count)."""
    removed_count = 0
    absent_count = 0
    for relative, expected_sha256 in MOVED_FILES:
        target = root / relative
        if not target.exists():
            absent_count += 1
            continue
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected_sha256:
            raise ValueError(f"Refusing to delete modified file: {relative}")
        target.unlink()
        removed_count += 1
    return removed_count, absent_count


if __name__ == "__main__":
    removed_count, absent_count = clean()
    print(f"Removed: {removed_count}; already absent: {absent_count}")
