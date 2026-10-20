"""Portable QBC bootstrap command line: compile, run and content cache.

Run as ``python -m qrvm.qbc_cli`` from an installed Quar SDK environment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from frontend.quar.module_loader import ModuleLoader
from frontend.quar.semantic import SemanticAnalyzer
from .bytecode_format import wrap_legacy_program
from .bytecode_serialization import read_qbc, write_qbc, QBCError
from .bytecode_loader import run_loaded_bytecode
from .compiler import QRVMCompiler
from .vm import QRVM, QuarExit


def compile_source(source: Path):
    """Compile a source and its imports into a versioned QBC package."""
    loader = ModuleLoader(source.parent)
    program = loader.load(source)
    validated = SemanticAnalyzer().analyze(program)
    compiled = QRVMCompiler().compile(validated)
    return wrap_legacy_program(compiled), tuple(sorted(loader.module_records))


def compile_file(source: Path, destination: Path) -> None:
    """Write a portable QBC file; returns None."""
    package, _ = compile_source(source.resolve())
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Write through a sibling file so a failed compile never truncates an existing artifact.
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        write_qbc(temporary, package)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def run_file(source: Path, args=()) -> None:
    """Execute a verified QBC file, forwarding program arguments."""
    loaded = read_qbc(source)
    run_loaded_bytecode(QRVM(args=list(args)), loaded)


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compiler_fingerprint() -> str:
    """Identify bootstrap compiler components for cache invalidation."""
    root = Path(__file__).resolve().parent.parent
    modules = ('qrvm/compiler.py', 'qrvm/bytecode_serialization.py',
               'frontend/quar/lexer.py', 'frontend/quar/parser.py',
               'frontend/quar/semantic.py', 'frontend/quar/module_loader.py')
    digest = hashlib.sha256()
    for module in modules:
        digest.update(module.encode('utf-8'))
        digest.update((root / module).read_bytes())
    return digest.hexdigest()


def _cache_paths(source: Path, cache_dir: Path):
    identifier = hashlib.sha256(str(source.resolve()).encode('utf-8')).hexdigest()
    return cache_dir / f'{identifier}.qbc', cache_dir / f'{identifier}.json'


def _valid_cache_manifest(manifest: object, source: Path) -> bool:
    """Reject incomplete cache manifests before trusting their dependency list."""
    if not isinstance(manifest, dict):
        return False
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, dict) or str(source) not in dependencies:
        return False
    return all(
        isinstance(name, str) and isinstance(digest, str) and
        len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)
        for name, digest in dependencies.items()
    )


def cached_compile(source: Path, cache_dir: Path) -> tuple[Path, bool]:
    """Return (QBC path, cache hit); track transitive imported source files."""
    source = source.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    qbc_path, manifest_path = _cache_paths(source, cache_dir)
    if qbc_path.is_file() and manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if (_valid_cache_manifest(manifest, source) and
            manifest['format'] == 1 and manifest['source'] == str(source) and
            manifest['compiler'] == _compiler_fingerprint() and all(
                Path(name).is_file() and _fingerprint(Path(name)) == digest
                for name, digest in manifest['dependencies'].items()
            )):
                if (not isinstance(manifest.get('artifact_sha256'), str) or
                    _fingerprint(qbc_path) != manifest['artifact_sha256']):
                    raise ValueError('cached artifact fingerprint mismatch')
                read_qbc(qbc_path)
                return qbc_path, True
        except (OSError, ValueError, KeyError, TypeError, QBCError):
            pass
    package, dependencies = compile_source(source)
    hashes = {str(path): _fingerprint(path) for path in set(dependencies) | {source}}
    # Publish bytecode before manifest: an interrupted write cannot create a valid cache hit.
    temp_qbc = qbc_path.with_suffix('.qbc.tmp')
    temp_manifest = manifest_path.with_suffix('.json.tmp')
    try:
        write_qbc(temp_qbc, package)
        os.replace(temp_qbc, qbc_path)
        temp_manifest.write_text(json.dumps({
            'format': 1, 'source': str(source), 'dependencies': hashes,
            'compiler': _compiler_fingerprint(),
            'artifact_sha256': _fingerprint(qbc_path),
        }, sort_keys=True), encoding='utf-8')
        os.replace(temp_manifest, manifest_path)
    finally:
        temp_qbc.unlink(missing_ok=True)
        temp_manifest.unlink(missing_ok=True)
    return qbc_path, False


def main(argv=None) -> int:
    """Run the QBC command; return a process exit status."""
    parser = argparse.ArgumentParser(description='Visual Quar portable QBC runtime')
    sub = parser.add_subparsers(dest='command', required=True)
    compile_cmd = sub.add_parser('compile', help='compile .quar/.vq to .qbc')
    compile_cmd.add_argument('source', type=Path)
    compile_cmd.add_argument('-o', '--output', type=Path)
    run_cmd = sub.add_parser('run', help='run a compiled .qbc file')
    run_cmd.add_argument('bytecode', type=Path)
    run_cmd.add_argument('program_args', nargs=argparse.REMAINDER)
    cache_cmd = sub.add_parser('cached-run', help='compile if changed, then run')
    cache_cmd.add_argument('source', type=Path)
    cache_cmd.add_argument('--cache-dir', type=Path)
    cache_cmd.add_argument('program_args', nargs=argparse.REMAINDER)
    options = parser.parse_args(argv)
    try:
        if options.command == 'compile':
            compile_file(options.source, options.output or options.source.with_suffix('.qbc'))
        elif options.command == 'run':
            run_file(options.bytecode, options.program_args)
        else:
            directory = options.cache_dir or options.source.parent / '.quar-cache'
            artifact, hit = cached_compile(options.source, directory)
            run_file(artifact, options.program_args)
        return 0
    except QuarExit as exc:
        return exc.code
    except (OSError, ValueError, RuntimeError, QBCError) as exc:
        print(f'QBC error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
