"""Standalone CFG borrow analysis demonstration (Python analyzer, not .vq)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from qrvm.control_flow import ControlFlowGraph, FlowNode, FlowEdge
from qrvm.borrow_flow import BorrowFlow
from qrvm.borrow_cfg import analyze_borrow_cfg
from qrvm.ownership_analysis import OwnershipError

cfg = ControlFlowGraph(tuple(FlowNode(i, 'statement') for i in range(4)),
                       (FlowEdge(0, 1), FlowEdge(0, 2), FlowEdge(1, 3), FlowEdge(2, 3)), 0, 3)

def transfer(node, flow):
    if node.id == 1:
        return flow.borrow('value', 'ref')
    if node.id == 3:
        flow.write('value')
    return flow

try:
    analyze_borrow_cfg(cfg, BorrowFlow.empty().declare('value'), transfer)
except OwnershipError as exc:
    print('Expected CFG conflict:', exc)
else:
    raise SystemExit('FAIL: conflict was not detected')

loop = ControlFlowGraph(tuple(FlowNode(i, 'statement') for i in range(4)),
                        (FlowEdge(0, 1), FlowEdge(1, 2), FlowEdge(2, 1), FlowEdge(2, 3)), 0, 3)
result = analyze_borrow_cfg(loop, BorrowFlow.empty().declare('value'),
                            lambda node, flow: flow)
assert result.at(3) is not None
print('PASS: CFG backedge converged; branch conflict rejected')
