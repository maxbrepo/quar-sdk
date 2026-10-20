"""Run the scoped CFG analysis on representative Visual Quar AST nodes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.quar import ast_nodes as ast
from qrvm.borrow_scoped_cfg import analyze_scoped_cfg
from qrvm.ownership_analysis import OwnershipError


def main():
    statements = [
        ast.VariableDeclaration('int', 'counter', ast.Integer(0)),
        ast.WhileStatement(ast.Boolean(True), [
            ast.VariableDeclaration('int', 'temporary', ast.Integer(1)),
            ast.Assignment('counter', ast.Variable('temporary')),
        ]),
        ast.VariableDeclaration('int', 'result', ast.Variable('counter')),
    ]
    result = analyze_scoped_cfg(statements)
    print(f'CFG analysis converged: {result.analysis.facts} facts')
    try:
        analyze_scoped_cfg(statements + [
            ast.VariableDeclaration('int', 'invalid', ast.Variable('temporary')),
        ])
    except OwnershipError as exc:
        print(f'Expected expired-scope conflict: {exc}')
    else:
        raise AssertionError('Expired local was not rejected')
    print('PASS: scoped CFG branch and loop lifetimes')


if __name__ == '__main__':
    main()
