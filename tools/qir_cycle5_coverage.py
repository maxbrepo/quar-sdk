"""Opt-in Cycle 5 QIR coverage audit against the validated QRVM baseline.

This tool does not change compilation, execute QIR, or import the legacy IR.
It reports direct AST-to-QIR lowering coverage and QRVM output separately.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path

from frontend.quar.ast_nodes import FunctionDefinition
from frontend.quar.qir.ast_lowering import QIRASTLoweringError, lower_ast_function
from frontend.quar.qir.validation import validate_function
from main import build_frontend
from qrvm.bytecode_format import wrap_legacy_program
from qrvm.bytecode_verifier import verify_bytecode
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM

PROFILES = ("typed", "inferred", "mixed")
CHAPTER_SAMPLES = (
    (1, "01 primitives/ch1 forward and mutual functions.vq"),
    (2, "02 operators expressions/c4 chapter2 function parity.vq"),
    (3, "03 conditions/c4 chapter3 function parity.vq"),
    (4, "04 loops/c4 ch4 callback loop parity.vq"),
    (5, "05 types/c4 ch5 advanced function parity.vq"),
)


def inspect_sample(sdk_root: Path, chapter: int, profile: str, relative: str) -> dict:
    """Return a deterministic report for one real source and its existing QRVM run."""
    path = sdk_root / "examples" / "0.0.5" / profile / relative
    source = path.read_text(encoding="utf-8")
    program, _ = build_frontend(source)
    package = QRVMCompiler().compile(program)
    verify_bytecode(wrap_legacy_program(package))
    output = io.StringIO()
    vm = QRVM()
    with contextlib.redirect_stdout(output):
        vm.run(package)
    if vm.stack:
        raise RuntimeError(f"Nonempty QRVM stack: {path}")

    functions = []
    for function in program:
        if not isinstance(function, FunctionDefinition):
            continue
        try:
            qir = lower_ast_function(function)
            validate_function(qir)
        except QIRASTLoweringError as exc:
            functions.append({"name": function.name, "qir": "unsupported", "reason": str(exc)})
        else:
            functions.append({
                "name": function.name,
                "qir": "lowered",
                "return_type": qir.return_type.name,
                "parameter_types": [p.type.name for p in qir.parameters],
                "block_count": len(qir.blocks),
                "opcodes": [ins.opcode for block in qir.blocks for ins in block.instructions],
            })

    return {
        "chapter": chapter,
        "profile": profile,
        "source": path.relative_to(sdk_root).as_posix(),
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "qrvm": "passed",
        "qrvm_stdout": output.getvalue(),
        "functions": functions,
    }


def audit(sdk_root: Path) -> dict:
    """Audit 15 curated Cycle 4 programs without modifying the SDK pipeline."""
    samples = [inspect_sample(sdk_root, chapter, profile, relative)
               for chapter, relative in CHAPTER_SAMPLES for profile in PROFILES]
    comparisons = []
    for chapter, _ in CHAPTER_SAMPLES:
        chapter_samples = [sample for sample in samples if sample["chapter"] == chapter]
        outputs = {sample["qrvm_stdout"] for sample in chapter_samples}
        comparisons.append({
            "chapter": chapter,
            "qrvm_output_parity": len(outputs) == 1,
            "direct_qir_supported_functions": sum(
                f["qir"] == "lowered" for sample in chapter_samples for f in sample["functions"]
            ),
            "direct_qir_unsupported_functions": sum(
                f["qir"] == "unsupported" for sample in chapter_samples for f in sample["functions"]
            ),
        })
    return {
        "checkpoint": "QIR-01",
        "scope": "diagnostic only; not QIR execution or backend parity",
        "samples": samples,
        "chapter_comparisons": comparisons,
    }


def main() -> int:
    """Write a machine-readable coverage report; return nonzero for QRVM parity loss."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    report = audit(args.sdk_root.resolve())
    payload = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if all(item["qrvm_output_parity"] for item in report["chapter_comparisons"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
