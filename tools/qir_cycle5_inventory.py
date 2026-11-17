"""Reproducible Cycle 5 QIR migration inventory; never claims execution parity.

Only numbered Chapter 1-18 example entrypoints form the initial denominator.
Other examples, module dependencies and test fixtures are reported separately.
No source is executed and no compiler behavior is modified by this tool.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

PROFILES = frozenset({"typed", "inferred", "mixed"})
CHAPTER_PATTERN = re.compile(r"^(0[1-9]|1[0-8])(?:\b|[_ -])")
ERROR_HINT = re.compile(r"(?:^|[\s_-])(error|invalid|fail|reject|overflow|underflow)(?:[\s_.-]|$)", re.I)
INPUT_HINT = re.compile(r"(?:^|[\s_-])(input|interactive)(?:[\s_.-]|$)", re.I)


def build_inventory(root: Path) -> dict:
    """Return a stable, hash-identified inventory of actual .vq example files."""
    examples = root / "examples"
    if not examples.is_dir():
        raise FileNotFoundError(f"Examples directory not found: {examples}")
    entries = []
    excluded = []
    for path in sorted(examples.rglob("*.vq")):
        parts = path.relative_to(examples).parts
        relative = path.relative_to(root).as_posix()
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        record = {"path": relative, "sha256": sha}
        if len(parts) < 4 or parts[1] not in PROFILES:
            excluded.append({**record, "reason": "outside version/profile/chapter layout"})
            continue
        version, profile, category = parts[:3]
        match = CHAPTER_PATTERN.match(category)
        if match is None:
            excluded.append({**record, "reason": "outside numbered Chapters 1-18"})
            continue
        chapter = int(match.group(1))
        # A chapter-13 example project contains a main.vq plus imported modules.
        # Imported modules are source files, not independent runnable programs.
        if chapter == 13 and len(parts) > 4 and path.name != "main.vq":
            excluded.append({**record, "reason": "chapter 13 imported module"})
            continue
        if chapter == 13 and len(parts) > 4 and path.name == "main.vq":
            pass
        elif len(parts) > 4:
            excluded.append({**record, "reason": "nested source requires separate entrypoint review"})
            continue
        name = path.stem
        entries.append({**record, "version": version, "profile": profile,
                        "chapter": chapter,
                        "candidate_negative": bool(ERROR_HINT.search(name)),
                        "candidate_interactive": bool(INPUT_HINT.search(name) or "input" in parts),
                        "qir_status": "pending"})
    chapters = []
    for chapter in range(1, 19):
        chapter_entries = [e for e in entries if e["chapter"] == chapter]
        chapters.append({"chapter": chapter, "total": len(chapter_entries),
                         "verified": 0, "percent": 0.0,
                         "profiles": {p: sum(e["profile"] == p for e in chapter_entries)
                                      for p in ("typed", "inferred", "mixed")},
                         "candidate_negative": sum(e["candidate_negative"] for e in chapter_entries),
                         "candidate_interactive": sum(e["candidate_interactive"] for e in chapter_entries)})
    digest = hashlib.sha256("\n".join(f'{e["path"]}:{e["sha256"]}' for e in entries).encode()).hexdigest()
    return {"checkpoint": "QIR-02", "scope": "static inventory; no QIR-to-QRVM program parity proven",
            "catalog_sha256": digest, "total_programs": len(entries),
            "verified_programs": 0, "qir_percent": 0.0,
            "chapter_progress": chapters, "programs": entries,
            "excluded_sources": excluded, "total_source_files": len(entries) + len(excluded)}


def main() -> int:
    """Write the baseline report and exit without running any example programs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_inventory(args.sdk_root.resolve())
    content = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
