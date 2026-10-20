"""Exercise lexical scopes in the standalone Visual Quar AST analyzer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.quar import ast_nodes as ast
from qrvm.borrow_ast_scopes import analyze_scoped_ast
from qrvm.ownership_analysis import OwnershipError


def declare(name):
    return ast.VariableDeclaration('int', name, ast.Integer(1))


program = [
    declare('x'),
    ast.IfStatement(ast.Variable('x'), [declare('branch_local')], []),
    ast.WhileStatement(ast.Variable('x'), [declare('loop_local')]),
    ast.Assignment('x', ast.Integer(2)),
]
result = analyze_scoped_ast(program)
assert all(set(path.lifetime.declared) == {'x'} for path in result.flow.paths)
assert result.loop_applications > 0

try:
    analyze_scoped_ast(program + [ast.Assignment('loop_local', ast.Integer(3))])
except OwnershipError as exc:
    print(f'Expected expired-scope conflict: {exc}')
else:
    raise AssertionError('Out-of-scope access was not rejected')

print('PASS: AST branch and loop locals expire at lexical scope exit')
