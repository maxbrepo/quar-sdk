"""Validate chapter 12 VM opcode integration before regression execution."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qrvm.instructions import OpCode


def test_error_handling_opcodes() -> None:
    required = ("TRY_CATCH", "THROW", "ASSERT", "PANIC")
    missing = [name for name in required if not hasattr(OpCode, name)]
    assert not missing, f"Missing QRVM instructions: {', '.join(missing)}"


if __name__ == "__main__":
    test_error_handling_opcodes()
    print("Chapter 12 opcode integration: PASS")
