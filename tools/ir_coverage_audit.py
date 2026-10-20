"""Report AST node coverage in the current Quar IR lowering layer.

This is a structural audit, not proof of runtime or semantic equivalence.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AST_PATH = ROOT / 'frontend/quar/ast_nodes.py'
BUILDER_PATH = ROOT / 'frontend/quar/ir/builder.py'


def collect_ast_classes():
    tree = ast.parse(AST_PATH.read_text(encoding='utf-8'))
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


def collect_lowered_classes():
    tree = ast.parse(BUILDER_PATH.read_text(encoding='utf-8'))
    handled = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'isinstance' and len(node.args) >= 2:
            target = node.args[1]
            candidates = target.elts if isinstance(target, ast.Tuple) else [target]
            handled.update(item.id for item in candidates if isinstance(item, ast.Name))
    return handled


def coverage():
    names = collect_ast_classes()
    handled = collect_lowered_classes()
    infrastructure = {'FunctionParameter', 'FunctionDefinition', 'ImportStatement', 'TypeField', 'SwitchCase', 'MatchArm', 'EnumVariant', 'ClassField', 'ClassConstructor', 'ClassMethod'}
    unsupported = sorted(names - handled - infrastructure)
    return sorted((names & handled)), unsupported, sorted(names & infrastructure)


if __name__ == '__main__':
    supported, missing, infrastructure = coverage()
    print(f'AST classes with isinstance handling in IR builder: {len(supported)}')
    print(f'AST classes without direct IR builder handling: {len(missing)}')
    for name in missing:
        print(f'  - {name}')
    print(f'AST classes handled as structural metadata elsewhere: {len(infrastructure)}')
    print('NOTE: Structural audit only; bytecode/QRVM equivalence requires separate tests.')
