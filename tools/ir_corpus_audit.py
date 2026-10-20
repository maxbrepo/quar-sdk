"""Audit real Visual Quar examples for IR lowering and QRVM bytecode parity.

This does not execute programs: runtime parity is a separate test phase.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.quar.ast_nodes import FunctionDefinition, ImportStatement
from frontend.quar.ir.builder import lower_function_body, lower_statement
from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from qrvm.compiler import QRVMCompiler
from qrvm.ir_bridge import to_ast

ROOT = Path(__file__).resolve().parents[1]


def audit_file(path):
    source = path.read_text(encoding='utf-8')
    try:
        statements = Parser(Lexer(source).tokenize()).parse()
    except Exception as exc:
        return 'parse_error', type(exc).__name__
    try:
        for node in statements:
            if isinstance(node, FunctionDefinition):
                lower_function_body(node)
            elif not isinstance(node, ImportStatement):
                lower_statement(node)
    except Exception as exc:
        return 'ir_error', f'{type(exc).__name__}: {exc}'
    # A whole-program comparison is meaningful only for standalone programs.
    if any(isinstance(node, ImportStatement) for node in statements):
        return 'lowered_imports', 'imports require project-level resolution'
    try:
        # Function bodies are lowered above; preserve definitions for the
        # compatibility compiler until the IR module-to-bytecode path exists.
        converted = [node if isinstance(node, FunctionDefinition)
                     else to_ast(lower_statement(node))
                     for node in statements]
        direct = QRVMCompiler().compile(statements)
        via_ir = QRVMCompiler().compile(converted)
        if direct['instructions'] != via_ir['instructions']:
            return 'bytecode_mismatch', 'instruction sequences differ'
    except Exception as exc:
        return 'compile_error', f'{type(exc).__name__}: {exc}'
    return 'bytecode_equal', ''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT / 'examples')
    parser.add_argument('--details', action='store_true')
    args = parser.parse_args()
    files = sorted(args.root.rglob('*.vq'))
    counts = Counter()
    problems = []
    for path in files:
        status, detail = audit_file(path)
        counts[status] += 1
        if status not in ('bytecode_equal', 'lowered_imports'):
            problems.append((str(path.relative_to(args.root)), status, detail))
    print(f'Files: {len(files)}')
    for status, count in sorted(counts.items()):
        print(f'{status}: {count}')
    if args.details:
        for name, status, detail in problems:
            print(f'{name}: {status}: {detail}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
