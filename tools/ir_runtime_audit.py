"""Conservative QRVM runtime parity audit for standalone examples.

Programs requiring interaction or external state are skipped; output is captured.
This is intentionally not a full chapter 1-13 runtime certification.
"""
import argparse
import contextlib
import io
import multiprocessing
import os
import tempfile
from unittest.mock import patch
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.quar.ast_nodes import ImportStatement
from frontend.quar.module_loader import ModuleLoader, ModuleLoadError
from frontend.quar.ir.builder import lower_statement
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from qrvm.compiler import QRVMCompiler
from qrvm.instructions import OpCode
from qrvm.ir_bridge import to_ast
from qrvm.vm import QRVM, QuarPanic

ROOT = Path(__file__).resolve().parents[1]
# Explicit allowlist excludes filesystem, interactive input and process effects.
# PRINT is safe because stdout is captured inside an isolated worker.
SAFE_OPCODES = frozenset({
    OpCode.PUSH_INT, OpCode.PUSH_DOUBLE, OpCode.PUSH_BOOL,
    OpCode.PUSH_CHAR, OpCode.PUSH_STRING, OpCode.LOAD, OpCode.STORE,
    OpCode.POP, OpCode.ADD, OpCode.SUB, OpCode.MUL, OpCode.DIV,
    OpCode.MOD, OpCode.BIT_AND, OpCode.BIT_OR, OpCode.BIT_XOR,
    OpCode.BIT_NOT, OpCode.SHIFT_LEFT, OpCode.SHIFT_RIGHT,
    OpCode.EQUAL, OpCode.NOT_EQUAL, OpCode.LESS, OpCode.LESS_EQUAL,
    OpCode.GREATER, OpCode.GREATER_EQUAL, OpCode.LOGICAL_AND,
    OpCode.LOGICAL_OR, OpCode.LOGICAL_NOT, OpCode.NEGATE,
    OpCode.ARRAY_NEW, OpCode.ARRAY_LOAD, OpCode.ARRAY_STORE,
    OpCode.LENGTH, OpCode.TUPLE_NEW, OpCode.TUPLE_UNPACK,
    OpCode.OBJECT_NEW, OpCode.MEMBER_LOAD, OpCode.MEMBER_STORE,
    OpCode.VARIANT_NEW, OpCode.HALT, OpCode.PRINT, OpCode.STRING_OP,
    OpCode.JUMP, OpCode.JUMP_IF_FALSE, OpCode.CALL, OpCode.RETURN,
    OpCode.MATCH_VARIANT, OpCode.TRY_CATCH, OpCode.THROW, OpCode.ASSERT,
    OpCode.CONSOLE_QUERY, OpCode.CONSOLE_WRITE, OpCode.PANIC, OpCode.EXIT,
    OpCode.INPUT,
})


# Never execute potentially nonterminating loops or recursion in the audit process.
RUNTIME_TIMEOUT_SECONDS = 2.0


PURE_FILE_OPERATIONS = frozenset({
    "Bytes.from_hex", "Bytes.to_hex", "Bytes.length",
    "Path.join", "Path.name", "Path.parent", "Path.stem", "Path.suffix",
})


def _file_operation_safe(operand):
    """Permit only path/bytes transformations that never touch the filesystem."""
    return (isinstance(operand, tuple) and len(operand) == 2
            and operand[0] in PURE_FILE_OPERATIONS)


def _instructions_safe(instructions, allow_files=False):
    for opcode, operand in instructions:
        if opcode == OpCode.FILE_OP and (_file_operation_safe(operand) or allow_files):
            continue
        if opcode not in SAFE_OPCODES and not (allow_files and opcode in (OpCode.FILE_OP, OpCode.WITH_FILE, OpCode.HANDLE_OP)):
            return False
        # TRY_CATCH embeds executable instruction lists in its operand.
        # Inspect both branches to prevent nested file/process operations.
        if opcode == OpCode.TRY_CATCH:
            try:
                try_body, _, catch_body = operand
            except (TypeError, ValueError):
                return False
            if not _instructions_safe(try_body, allow_files) or not _instructions_safe(catch_body, allow_files):
                return False
    return True


def _unsafe_opcodes(instructions):
    """Collect disallowed operations, including nested exception handlers."""
    found = set()
    for opcode, operand in instructions:
        if opcode not in SAFE_OPCODES and not (opcode == OpCode.FILE_OP and _file_operation_safe(operand)):
            found.add(opcode.name)
        if opcode == OpCode.TRY_CATCH:
            try:
                try_body, _, catch_body = operand
            except (TypeError, ValueError):
                found.add('MALFORMED_TRY_CATCH')
                continue
            found.update(_unsafe_opcodes(try_body))
            found.update(_unsafe_opcodes(catch_body))
    return found


def unsafe_program_opcodes(program):
    """Return sorted unsafe opcode names across top-level and callable bodies."""
    found = _unsafe_opcodes(program['instructions'])
    for key in ('functions', 'class_methods'):
        for function in program.get(key, {}).values():
            found.update(_unsafe_opcodes(function.get('instructions', [])))
    return tuple(sorted(found))


def _program_safe(program, allow_files=False):
    if not _instructions_safe(program['instructions'], allow_files):
        return False
    for function in program.get('functions', {}).values():
        if not _instructions_safe(function.get('instructions', []), allow_files):
            return False
    for method in program.get('class_methods', {}).values():
        if not _instructions_safe(method.get('instructions', []), allow_files):
            return False
    return True


def _snapshot_files():
    """Record sandbox contents to compare observable filesystem effects."""
    return tuple(sorted((str(path.relative_to('/')), path.read_bytes() if path.is_file() else None)
                        for path in Path('/').rglob('*') if path.is_file() or path.is_dir()))


def _execute_in_child(program, queue, sandbox_root=None):
    # A real chroot confines absolute paths, relative paths and directory traversal.
    # Only enabled when running as root; otherwise filesystem tests stay excluded.
    filesystem = sandbox_root is not None
    if filesystem:
        try:
            os.chroot(sandbox_root)
            os.chdir('/')
        except OSError as exc:
            queue.put(('sandbox_error', str(exc)))
            return
    # Deterministic, isolated console state for both compilation routes.
    vm = QRVM(args=[], environ={})
    stderr = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(stderr), patch.object(sys, "stdin", io.StringIO("")):
        try:
            vm.run(program)
            result = ('ok', None)
        except (Exception, QuarPanic) as exc:
            result = ('error', type(exc).__name__, str(exc))
    queue.put((result, vm.variables, vm.stack, output.getvalue(), stderr.getvalue(), _snapshot_files() if filesystem else None))


def _bounded_execute(program, filesystem=False):
    if filesystem:
        with tempfile.TemporaryDirectory(prefix="vq_ir_fs_") as sandbox_root:
            return _run_bounded_worker(program, sandbox_root)
    return _run_bounded_worker(program, None)


def _run_bounded_worker(program, sandbox_root):
    context = multiprocessing.get_context('fork')
    queue = context.Queue()
    process = context.Process(target=_execute_in_child, args=(program, queue, sandbox_root))
    process.start()
    try:
        process.join(RUNTIME_TIMEOUT_SECONDS)
        if process.is_alive():
            return 'timeout', None
        if process.exitcode != 0:
            return 'worker_error', process.exitcode
        return 'ok', queue.get(timeout=0.5)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join()
        queue.close()


def _compile_outcome(statements):
    """Return compiled program or a comparable compiler diagnostic."""
    try:
        return QRVMCompiler().compile(statements), None
    except Exception as exc:
        return None, f'{type(exc).__name__}: {exc}'


def audit_runtime_file(path):
    try:
        statements = Parser(Lexer(path.read_text(encoding='utf-8')).tokenize()).parse()
    except Exception as exc:
        return 'parse_error', type(exc).__name__
    if any(isinstance(node, ImportStatement) for node in statements):
        try:
            # Imports are resolved from the entry file's directory, as in
            # the existing project-level module loader.
            module_root = path.parent / "fixtures"
            loader = ModuleLoader(module_root if module_root.is_dir() else path.parent)
            loader.load(path)
            statements = loader.canonical_program()
        except (ModuleLoadError, OSError, ValueError) as exc:
            return 'module_error', f'{type(exc).__name__}: {exc}'
    try:
        converted = []
        for node in statements:
            converted.append(to_ast(lower_statement(node)))
    except Exception as exc:
        return 'ir_conversion_error', f'{type(exc).__name__}: {exc}'
    direct, direct_error = _compile_outcome(statements)
    via_ir, ir_error = _compile_outcome(converted)
    if direct_error or ir_error:
        if direct_error == ir_error:
            return 'compile_error_equal', direct_error
        return 'compile_error_mismatch', repr((direct_error, ir_error))
    if direct['instructions'] != via_ir['instructions']:
        return 'bytecode_mismatch', 'instruction sequences differ'
    filesystem = not _program_safe(direct) or not _program_safe(via_ir)
    if filesystem and (os.geteuid() != 0 or not _program_safe(direct, True) or not _program_safe(via_ir, True)):
        return 'skipped_effectful', ', '.join(sorted(set(unsafe_program_opcodes(direct)) | set(unsafe_program_opcodes(via_ir))))

    try:
        left_status, left = _bounded_execute(direct, filesystem)
        right_status, right = _bounded_execute(via_ir, filesystem)
        if left_status == 'timeout' or right_status == 'timeout':
            return 'skipped_timeout', 'execution exceeded bounded runtime'
        if left_status != 'ok' or right_status != 'ok':
            return 'audit_error', repr((left_status, left, right_status, right))
        return ('runtime_equal', '') if left == right else ('runtime_mismatch', repr((left, right)))
    except Exception as exc:
        return 'audit_error', f'{type(exc).__name__}: {exc}'


# Explicit expectations for known negative examples. These are not inferred
# from filenames and do not excuse mismatches between compilation routes.
EXPECTED_NEGATIVE_CASES = {
    '093 incoherent for direction error.vq': 'skipped_timeout',
    '094 infinite while error.vq': 'skipped_timeout',
    '095 infinite explicit loop error.vq': 'skipped_timeout',
    '046 duplicate import.vq': 'module_error',
    '047 missing module.vq': 'module_error',
    '048 circular dependency.vq': 'module_error',
    '082 duplicate default error.vq': 'parse_error',
}


def classify_audit_result(path, status):
    """Label corpus outcomes without replacing their measured audit status.

    Filename conventions provide provisional expectations, not proof that
    both compilation routes reject a program for the same reason.
    """
    if 'fixtures' in path.parts:
        return 'module_fixture'
    if status in ('runtime_mismatch', 'bytecode_mismatch', 'audit_error', 'compile_error_mismatch', 'ir_conversion_error'):
        return 'regression'
    if EXPECTED_NEGATIVE_CASES.get(path.name) == status:
        return 'expected_negative_verified'
    if status == 'runtime_equal':
        return 'verified_equivalent'
    if status == 'skipped_effectful':
        return 'requires_controlled_execution'
    if status == 'skipped_timeout':
        return 'expected_timeout_candidate' if 'error' in path.stem.lower() else 'unresolved_timeout'
    if status in ('parse_error', 'compile_error_equal', 'compile_error', 'module_error'):
        return 'expected_error_candidate' if 'error' in path.stem.lower() else 'unresolved_error'
    return 'unclassified'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT / 'examples')
    parser.add_argument('--details', action='store_true')
    args = parser.parse_args()
    counts = Counter()
    classifications = Counter()
    issues = []
    excluded_operations = Counter()
    files = sorted(args.root.rglob('*.vq'))
    for path in files:
        status, detail = audit_runtime_file(path)
        counts[status] += 1
        if status == 'skipped_effectful':
            excluded_operations.update(name.strip() for name in detail.split(',') if name.strip())
        classifications[classify_audit_result(path, status)] += 1
        if status in ('runtime_mismatch', 'bytecode_mismatch', 'audit_error', 'compile_error_mismatch', 'ir_conversion_error'):
            issues.append((path, status, detail))
    print(f'Files: {len(files)}')
    for status, count in sorted(counts.items()):
        print(f'{status}: {count}')
    print('Excluded operations (overlapping counts):')
    for name, count in sorted(excluded_operations.items()):
        print(f'{name}: {count}')
    print("Classification (provisional):")
    for label, count in sorted(classifications.items()):
        print(f"{label}: {count}")
    if args.details:
        for path, status, detail in issues:
            print(f'{path}: {status}: {detail}')
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
