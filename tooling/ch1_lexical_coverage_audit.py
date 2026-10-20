"""Measure opt-in lexical compilation coverage of official Visual Quar examples.

A successful backend compilation is not proof of equivalent program behavior.
This audit deliberately distinguishes QRVM lowering, C emission and native build.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from backend.c.codegen import CCodeGenerator
from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from main import (
    EXPECTED_TEST_ERRORS, collect_batch_sources, execute_regression_source,
    extract_test_number, regression_project_root,
)
from qrvm.compiler import QRVMCompiler


@dataclass(frozen=True)
class AuditResult:
    source: str
    profile: str
    stage: str
    reason: str = ""


def source_profile(path: Path) -> str:
    return next((part for part in path.parts if part in {"typed", "inferred", "mixed"}), "other")


def audit(root: Path, *, compile_c: bool = False) -> list[AuditResult]:
    """Return one result per official example without changing its source tree."""
    root = root.resolve()
    results = []
    compiler_path = shutil.which("cc") if compile_c else None
    for path in collect_batch_sources(root):
        relative_path = str(path.relative_to(root))
        profile = source_profile(path)
        if extract_test_number(path) in EXPECTED_TEST_ERRORS:
            results.append(AuditResult(relative_path, profile, "expected_error"))
            continue
        status, reason = execute_regression_source(path)
        if status != "PASS":
            results.append(AuditResult(relative_path, profile, "baseline_failed", f"{status}: {reason}"))
            continue
        try:
            program = ModuleLoader(regression_project_root(path)).load(path)
            semantic = SemanticAnalyzer(allow_lexical_shadowing=True)
            validated = semantic.analyze(program)
        except Exception as error:
            results.append(AuditResult(relative_path, profile, "frontend_blocked", f"{type(error).__name__}: {error}"))
            continue
        try:
            QRVMCompiler().compile(
                validated, lexical=True, allow_inference=profile in {"inferred", "mixed"}
            )
        except Exception as error:
            results.append(AuditResult(relative_path, profile, "qrvm_blocked", f"{type(error).__name__}: {error}"))
            continue
        try:
            generated = CCodeGenerator().generate(
                validated, semantic.variables, lexical=True,
                allow_inference=profile in {"inferred", "mixed"},
            )
        except Exception as error:
            results.append(AuditResult(relative_path, profile, "quarc_blocked", f"{type(error).__name__}: {error}"))
            continue
        if compiler_path:
            with tempfile.TemporaryDirectory(prefix="vq_lexical_audit_") as temp:
                source = Path(temp) / "program.c"
                source.write_text(generated, encoding="utf-8")
                try:
                    build = subprocess.run(
                        [compiler_path, "-std=c11", "-Wall", "-Werror", "-fsyntax-only", str(source)],
                        capture_output=True, text=True, timeout=10, check=False,
                    )
                except subprocess.TimeoutExpired:
                    results.append(AuditResult(relative_path, profile, "native_blocked", "C compilation timeout"))
                    continue
                if build.returncode:
                    diagnostics = build.stderr.splitlines()
                    detail = next(
                        (line.strip() for line in diagnostics if "error:" in line),
                        diagnostics[0].strip() if diagnostics else "C compilation error",
                    )
                    results.append(AuditResult(relative_path, profile, "native_blocked", detail))
                    continue
            results.append(AuditResult(relative_path, profile, "native_compiled"))
        else:
            results.append(AuditResult(relative_path, profile, "c_emitted"))
    return results


def report(results: list[AuditResult]) -> dict:
    """Summarize stage counts with representative failure categories."""
    stages = Counter(result.stage for result in results)
    profiles = defaultdict(Counter)
    blockers = Counter()
    examples = {}
    for item in results:
        profiles[item.profile][item.stage] += 1
        if item.stage.endswith("_blocked"):
            category = item.reason.split(": ", 1)[-1].splitlines()[0]
            key = f"{item.stage}: {category}"
            blockers[key] += 1
            examples.setdefault(key, item.source)
    return {
        "total": len(results),
        "stages": dict(sorted(stages.items())),
        "profiles": {p: dict(sorted(c.items())) for p, c in sorted(profiles.items())},
        "top_blockers": [
            {"category": key, "count": count, "example": examples[key]}
            for key, count in blockers.most_common(20)
        ],
    }


def markdown(summary: dict) -> str:
    lines = [
        "# Visual Quar 0.0.4 — Official lexical compatibility audit", "",
        "The audit checks the official non-interactive `.vq` corpus against the",
        "opt-in lexical compilation route. Expected-error fixtures are excluded",
        "from success-path probing and counted separately. The default route",
        "remains unchanged. **Emitting C or passing a C syntax check does not",
        "establish runtime parity with QRVM.**", "",
        f"Official sources: **{summary['total']}**", "", "## Pipeline stages", "",
        "| Stage | Sources |", "|---|---:|",
    ]
    for stage, count in summary["stages"].items():
        lines.append(f"| {stage} | {count} |")
    lines += ["", "## Profiles", "", "| Profile | Stages |", "|---|---|"]
    for profile, stages in summary["profiles"].items():
        lines.append(f"| {profile} | " + ", ".join(f"{stage}: {count}" for stage, count in stages.items()) + " |")
    lines += ["", "## Leading blockers", "", "| Count | Category | Example |", "|---:|---|---|"]
    for item in summary["top_blockers"]:
        lines.append(f"| {item['count']} | {item['category'].replace('|', '/')} | {item['example'].replace('|', '/')} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples", type=Path, default=Path(__file__).resolve().parents[1] / "examples")
    parser.add_argument("--compile-c", action="store_true")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    options = parser.parse_args()
    data = report(audit(options.examples, compile_c=options.compile_c))
    encoded = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if options.json:
        options.json.write_text(encoded, encoding="utf-8")
    if options.markdown:
        options.markdown.write_text(markdown(data), encoding="utf-8")
    print(encoded, end="")


if __name__ == "__main__":
    main()
