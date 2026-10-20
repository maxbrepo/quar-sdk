"""Execute the Chapter 15.37 AST bridge prototype directly."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from frontend.quar.ast_nodes import Assignment, Integer, Variable, VariableDeclaration
from qrvm.borrow_ast import analyze_borrow_ast
from qrvm.borrow_flow import BorrowFlow
from qrvm.ownership_analysis import OwnershipError

program = [VariableDeclaration('int', 'x', Integer(1)),
           Assignment('x', Variable('x'))]
result = analyze_borrow_ast(program)
assert result.analysis.at(result.graph.exit) is not None

try:
    analyze_borrow_ast([Assignment('x', Integer(2))],
                       BorrowFlow.empty().declare('x').borrow('x', 'ref'))
except OwnershipError as error:
    print(f'Expected AST conflict: {error}')
else:
    raise AssertionError('Conflicting write was accepted')

print('PASS: AST declarations, assignments and borrow conflicts')
