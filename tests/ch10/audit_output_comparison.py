"""Compare deterministic QRVM output against the unmodified 0.0.3 repository.

Internal development audit, not needed by an installed SDK. Invocation:
python tests/ch10/audit_output_comparison.py /path/to/unmodified/0.0.3
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def capture_example_outputs(root: Path) -> dict:
    """Compile each noninteractive example and capture execution status and stdout."""
    from frontend.quar.lexer import Lexer
    from frontend.quar.parser import Parser
    from frontend.quar.semantic import SemanticAnalyzer
    from qrvm.compiler import QRVMCompiler
    from qrvm.vm import QRVM

    examples = root / "examples" / "0.0.3"
    outcomes = {}
    for source_file in sorted(examples.rglob("*.vq")):
        relative = source_file.relative_to(examples)
        if any(part in ("input", "fixtures", "XX modules") for part in relative.parts):
            continue
        content = source_file.read_text(encoding="utf-8")
        output = io.StringIO()
        outcome = {"sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
        try:
            with contextlib.redirect_stdout(output):
                ast = Parser(Lexer(content).tokenize()).parse()
                analyzed = SemanticAnalyzer().analyze(ast)
                bytecode = QRVMCompiler().compile(analyzed)
                QRVM().run(bytecode)
            outcome.update(status="ok", stdout=output.getvalue())
        except Exception as exc:
            outcome.update(status="error", error_type=type(exc).__name__)
        outcomes[relative.as_posix()] = outcome
    return outcomes


def run_in_tree(root: Path) -> dict:
    """Use a fresh interpreter to avoid mixing baseline and development imports."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker", str(root)],
        cwd=root, env=env, capture_output=True, text=True, check=True,
    )
    return json.loads(completed.stdout)


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        print(json.dumps(capture_example_outputs(Path(sys.argv[2]))))
        return 0
    if len(sys.argv) != 2:
        print(__doc__.strip())
        return 2
    baseline = run_in_tree(Path(sys.argv[1]).resolve())
    current = run_in_tree(ROOT)
    shared = baseline.keys() & current.keys()
    compared = 0
    differences = []
    for name in sorted(shared):
        before = baseline[name]
        after = current[name]
        if before["sha256"] != after["sha256"]:
            differences.append((name, "source changed: cannot compare automatically"))
            continue
        if before["status"] != after["status"]:
            differences.append((name, f"status {before['status']} -> {after['status']}"))
        elif before["status"] == "ok":
            compared += 1
            if before["stdout"] != after["stdout"]:
                differences.append((name, f"output {before['stdout']!r} -> {after['stdout']!r}"))
        elif before["error_type"] != after["error_type"]:
            differences.append((name, f"exception {before['error_type']} -> {after['error_type']}"))
    print(f"Shared source files: {len(shared)}")
    print(f"Successful outputs compared: {compared}")
    print(f"Differences: {len(differences)}")
    for name, detail in differences:
        print(f"DIFFERENCE: {name}: {detail}")
    return 1 if differences else 0


if __name__ == "__main__":
    sys.exit(main())
