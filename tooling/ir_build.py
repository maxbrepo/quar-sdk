"""Shared experimental build orchestration for Quar IR C output.

This component writes C artifacts but deliberately does not assume that
IR 0.1 represents a complete executable Quar program.
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import subprocess
import json

from backend.c.ir_codegen import IRCodeGenerator


class BuildError(RuntimeError):
    """A compiler or linker command failed."""


class CLayout(str, Enum):
    SINGLE = "single"
    SPLIT = "split"


@dataclass(frozen=True)
class CArtifacts:
    layout: CLayout
    sources: tuple[Path, ...]
    headers: tuple[Path, ...]


def emit_c(project, output_dir: Path, layout: CLayout | str) -> CArtifacts:
    """Write generated IR functions in a single or split C layout."""
    layout = CLayout(layout)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generator = IRCodeGenerator()
    outputs = ({"quar_generated.c": generator.generate(project)}
               if layout is CLayout.SINGLE else generator.generate_split(project))
    # Remove only artifacts tracked by the previous Quar emission.
    manifest = output_dir / ".quar_c_artifacts.json"
    previous = []
    if manifest.is_file():
        previous = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(previous, list) or not all(isinstance(n, str) for n in previous):
            raise ValueError("Invalid Quar C artifact manifest")
    for name in previous:
        if Path(name).name != name:
            raise ValueError("Unsafe filename in Quar C artifact manifest")
        if name not in outputs:
            (output_dir / name).unlink(missing_ok=True)
            (output_dir / (Path(name).stem + ".o")).unlink(missing_ok=True)
    sources = []
    headers = []
    for filename, contents in outputs.items():
        path = output_dir / filename
        path.write_text(contents, encoding="utf-8")
        if path.suffix == ".c":
            sources.append(path)
        elif path.suffix == ".h":
            headers.append(path)
    manifest.write_text(json.dumps(sorted(outputs), indent=2), encoding="utf-8")
    return CArtifacts(layout, tuple(sources), tuple(headers))


def compile_objects(artifacts: CArtifacts, output_dir: Path,
                    compiler: str = "gcc") -> tuple[Path, ...]:
    """Compile each C translation unit separately, without linking an entrypoint."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    objects = []
    for source in artifacts.sources:
        target = output_dir / (source.stem + ".o")
        target.unlink(missing_ok=True)
        command = [compiler, "-std=c11", "-c", str(source), "-o", str(target)]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, OSError) as exc:
            detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
            raise BuildError(f"C compilation failed for {source.name}: {detail}") from exc
        objects.append(target)
    return tuple(objects)


def link_executable(objects: tuple[Path, ...], target: Path,
                    compiler: str = "gcc") -> Path:
    """Link separately compiled objects into one executable."""
    if not objects:
        raise ValueError("Cannot link an empty set of object files")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    command = [compiler, *(str(obj) for obj in objects), "-o", str(target)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        detail = exc.stderr.strip() if isinstance(exc, subprocess.CalledProcessError) and exc.stderr else str(exc)
        raise BuildError(f"C linking failed for {target.name}: {detail}") from exc
    return target
