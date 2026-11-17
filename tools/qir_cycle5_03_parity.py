"""Reproducible full-program QIR-to-QRVM parity report for Cycle 5 QIR-03.

Only confirmed complete-program parity counts toward migration progress.
The immutable QIR-02 catalog fingerprint is checked before execution.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path

from frontend.quar.qir.program_lowering import lower_ast_program
from main import build_frontend
from qrvm.bytecode_format import wrap_legacy_program
from qrvm.bytecode_verifier import verify_bytecode
from qrvm.compiler import QRVMCompiler
from qrvm.qir_program_backend import compile_qir_program
from qrvm.vm import QRVM
from tools.qir_cycle5_inventory import build_inventory

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = tuple(
    f"examples/0.0.4/{profile}/01 primitives/ch1 constants and assignments.vq"
    for profile in ("typed", "inferred", "mixed")
)


def execute(package: dict) -> str:
    """Execute a verified bytecode package and return captured stdout."""
    verify_bytecode(wrap_legacy_program(package))
    output = io.StringIO()
    vm = QRVM()
    with contextlib.redirect_stdout(output):
        vm.run(package)
    if vm.stack:
        raise AssertionError("QRVM left values on the operand stack")
    return output.getvalue()


def build_report(root: Path) -> dict:
    """Return progress based only on complete, independently executed programs."""
    baseline = json.loads((root / "tests/data/qir/QIR_CYCLE5_02_INVENTORY.json").read_text(encoding="utf-8"))
    current = build_inventory(root)
    if (current["catalog_sha256"] != baseline["catalog_sha256"] or
            current["total_programs"] != baseline["total_programs"]):
        raise ValueError("QIR-02 inventory fingerprint changed: explicit rebaseline required")
    paths = {entry["path"] for entry in current["programs"]}
    if not set(SAMPLES) <= paths:
        raise ValueError("A QIR-03 sample is missing from the fixed catalog")

    verified = []
    for relative in SAMPLES:
        program, _ = build_frontend((root / relative).read_text(encoding="utf-8"))
        baseline_output = execute(QRVMCompiler().compile(program))
        qir = lower_ast_program(program)
        qir_output = execute(compile_qir_program(qir))
        if qir_output != baseline_output:
            raise AssertionError(f"QIR output differs from baseline: {relative}")
        verified.append({"path": relative, "output": qir_output, "status": "verified"})

    total = current["total_programs"]
    chapters = []
    for chapter in current["chapter_progress"]:
        count = sum(1 for entry in verified if next(p for p in current["programs"]
                    if p["path"] == entry["path"])["chapter"] == chapter["chapter"])
        chapters.append({"chapter": chapter["chapter"], "total": chapter["total"],
                         "verified": count,
                         "percent": round(100 * count / chapter["total"], 2) if chapter["total"] else None})
    return {"checkpoint": "QIR-03", "catalog_sha256": current["catalog_sha256"],
            "total_programs": total, "verified_programs": len(verified),
            "qir_percent": round(100 * len(verified) / total, 2),
            "chapter_progress": chapters, "verified_entries": verified,
            "scope": "Full-program parity for a linear i32 subset; no overflow/safety parity certification"}


def main() -> int:
    """Write a reproducible report, returning nonzero on any parity failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.sdk_root.resolve())
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
