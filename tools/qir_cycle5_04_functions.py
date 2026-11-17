"""Cycle 5 QIR-04: reproducible full-program parity for linear i32 functions.

The QIR-02 catalog remains frozen. Only explicitly selected, independently
executed source files contribute to the reported migration percentage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from frontend.quar.qir.program_lowering import lower_ast_program
from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import ROOT, SAMPLES as QIR03_SAMPLES, execute
from tools.qir_cycle5_inventory import build_inventory

_FUNCTION_CASES = (
    ("0.0.4", "inferred", "ch1 function and local values.vq"),
    ("0.0.4", "mixed", "ch1 function and local values.vq"),
    ("0.0.5", "typed", "ch1 function and local values.vq"),
    ("0.0.4", "inferred", "ch1 function scope isolation.vq"),
    ("0.0.4", "mixed", "ch1 function scope isolation.vq"),
    ("0.0.4", "typed", "ch1 function scope isolation.vq"),
)
SAMPLES = QIR03_SAMPLES + tuple(
    f"examples/{version}/{profile}/01 primitives/{name}"
    for version, profile, name in _FUNCTION_CASES
)


def build_report(root: Path) -> dict:
    """Execute both backends independently and count verified catalog entries."""
    baseline = json.loads((root / "tests/data/qir/QIR_CYCLE5_02_INVENTORY.json").read_text(encoding="utf-8"))
    current = build_inventory(root)
    if (current["catalog_sha256"] != baseline["catalog_sha256"] or
            current["total_programs"] != baseline["total_programs"]):
        raise ValueError("QIR-02 catalog changed: explicit rebaseline required")
    by_path = {item["path"]: item for item in current["programs"]}
    if not set(SAMPLES) <= set(by_path) or len(SAMPLES) != len(set(SAMPLES)):
        raise ValueError("QIR-04 sample set is missing or duplicated")
    verified = []
    for relative in SAMPLES:
        ast, _ = build_frontend((root / relative).read_text(encoding="utf-8"))
        old_output = execute(QRVMCompiler().compile(ast))
        profile = by_path[relative]["profile"]
        qir = lower_ast_program(ast, allow_inferred_declarations=profile != "typed")
        new_output = execute(compile_qir_program(qir))
        if old_output != new_output:
            raise AssertionError(f"QIR and AST QRVM outputs differ: {relative}")
        verified.append({"path": relative, "status": "verified", "output": new_output,
                         "qir_functions": len(qir.functions) - 1})
    chapter_progress = []
    for chapter in current["chapter_progress"]:
        count = sum(by_path[item["path"]]["chapter"] == chapter["chapter"] for item in verified)
        chapter_progress.append({"chapter": chapter["chapter"], "total": chapter["total"],
                                 "verified": count,
                                 "percent": round(100 * count / chapter["total"], 2) if chapter["total"] else None})
    return {"checkpoint": "QIR-04", "catalog_sha256": current["catalog_sha256"],
            "total_programs": current["total_programs"], "verified_programs": len(verified),
            "qir_percent": round(100 * len(verified) / current["total_programs"], 2),
            "chapter_progress": chapter_progress, "verified_entries": verified,
            "scope": "Linear i32 programs with direct calls; overflow and runtime safety parity not certified"}


def main() -> int:
    """Write the independently verified progress report."""
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
