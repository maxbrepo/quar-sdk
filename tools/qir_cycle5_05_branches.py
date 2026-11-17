"""QIR-05: reproduce scoped branch parity against the frozen QIR-02 catalog.

Only independently executed complete programs count toward migration progress.
The source catalog is not altered by this checkpoint.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from frontend.quar.qir.program_lowering import lower_ast_program
from main import build_frontend
from qrvm.compiler import QRVMCompiler
from qrvm.qir_program_backend import compile_qir_program
from tools.qir_cycle5_03_parity import ROOT, execute
from tools.qir_cycle5_04_functions import SAMPLES as QIR04_SAMPLES
from tools.qir_cycle5_inventory import build_inventory

_BRANCH_CASES = (
    ("0.0.4", "inferred", "nested scope baseline"),
    ("0.0.4", "mixed", "nested scope baseline"),
    ("0.0.5", "typed", "nested scope baseline"),
    *(("0.0.4", profile, name)
      for name in ("nested scope isolation", "outer assignment across scopes",
                   "sibling branch scopes")
      for profile in ("typed", "inferred", "mixed")),
)
SAMPLES = QIR04_SAMPLES + tuple(
    f"examples/{version}/{profile}/01 primitives/ch1 {name}.vq"
    for version, profile, name in _BRANCH_CASES
)
BASELINE = "tests/data/qir/QIR_CYCLE5_02_INVENTORY.json"


def build_report(root: Path) -> dict:
    """Return reproducible execution parity and catalog-based progress."""
    baseline = json.loads((root / BASELINE).read_text(encoding="utf-8"))
    current = build_inventory(root)
    if (current["catalog_sha256"] != baseline["catalog_sha256"] or
            current["total_programs"] != baseline["total_programs"]):
        raise ValueError("QIR-02 source catalog changed: explicit rebaseline required")
    by_path = {entry["path"]: entry for entry in current["programs"]}
    if len(SAMPLES) != len(set(SAMPLES)) or not set(SAMPLES) <= set(by_path):
        raise ValueError("QIR-05 sample set is missing or duplicated")
    verified = []
    for relative in SAMPLES:
        program, _ = build_frontend((root / relative).read_text(encoding="utf-8"))
        old_output = execute(QRVMCompiler().compile(program))
        profile = by_path[relative]["profile"]
        qir = lower_ast_program(program, allow_inferred_declarations=profile != "typed")
        new_output = execute(compile_qir_program(qir))
        if old_output != new_output:
            raise AssertionError(f"QIR/legacy QRVM output mismatch: {relative}")
        verified.append({"path": relative, "status": "verified", "output": new_output,
                         "qir_blocks": sum(len(f.blocks) for f in qir.functions)})
    progress = []
    for chapter in current["chapter_progress"]:
        count = sum(by_path[item["path"]]["chapter"] == chapter["chapter"]
                    for item in verified)
        progress.append({"chapter": chapter["chapter"], "total": chapter["total"],
                         "verified": count,
                         "percent": round(100 * count / chapter["total"], 2)
                         if chapter["total"] else None})
    return {"checkpoint": "QIR-05", "catalog_sha256": current["catalog_sha256"],
            "total_programs": current["total_programs"],
            "verified_programs": len(verified),
            "qir_percent": round(100 * len(verified) / current["total_programs"], 2),
            "chapter_progress": progress, "verified_entries": verified,
            "scope": "Acyclic i32 branches, lexical scope, SSA phi merges; no loop or overflow parity certification"}


def main() -> int:
    """Write the report under devlogs or stdout without modifying sources."""
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
