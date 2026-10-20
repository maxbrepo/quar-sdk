"""Regression tests for conservative QIR phi simplification."""
import unittest
from frontend.quar.qir.model import QBlock, QBranch, QFunction, QInstruction, QJump, QPhi, QReturn, QType, QValue
from frontend.quar.qir.optimize import simplify_phis
from frontend.quar.qir.validation import validate_function
I = QType('i32')
B = QType('bool')
def v(name, typ=I):
    return QValue(name, typ)

class TestPhiOptimization(unittest.TestCase):
    def diamond(self, left=None, right=None):
        left = left or v('x')
        right = right or v('x')
        return QFunction('choose', I, (v('x'), v('y'), v('flag', B)), (
            QBlock('entry', (), QBranch(v('flag', B), 'left', 'right')),
            QBlock('left', (), QJump('join')),
            QBlock('right', (), QJump('join')),
            QBlock('join', (), QReturn(v('merged')), (QPhi(v('merged'), (('left', left), ('right', right))),)),
        ))

    def test_identical_inputs_removed(self):
        fn = self.diamond()
        result = simplify_phis(fn)
        self.assertEqual(result.blocks[-1].phis, ())
        self.assertEqual(result.blocks[-1].terminator.value, v('x'))
        validate_function(result)

    def test_different_inputs_preserved(self):
        fn = self.diamond(right=v('y'))
        self.assertEqual(simplify_phis(fn), fn)

    def test_original_unchanged(self):
        fn = self.diamond()
        simplify_phis(fn)
        self.assertEqual(len(fn.blocks[-1].phis), 1)

    def test_idempotence(self):
        fn = self.diamond()
        self.assertEqual(simplify_phis(simplify_phis(fn)), simplify_phis(fn))

    def test_instruction_operands_rewritten(self):
        fn = self.diamond()
        blocks = list(fn.blocks)
        blocks[-1] = QBlock('join', (QInstruction('copy', (v('merged'),), v('result')),), QReturn(v('result')), blocks[-1].phis)
        result = simplify_phis(QFunction(fn.name, fn.return_type, fn.parameters, tuple(blocks)))
        self.assertEqual(result.blocks[-1].instructions[0].operands, (v('x'),))

    def test_loop_carried_phi_preserved(self):
        from frontend.quar.qir.ssa_loops import to_ssa_with_loops
        original = QFunction('loop', I, (v('initial'), v('step'), v('flag', B)), (
            QBlock('entry', (QInstruction('copy', (v('initial'),), v('count')),), QJump('head')),
            QBlock('head', (), QBranch(v('flag', B), 'body', 'exit')),
            QBlock('body', (QInstruction('add', (v('count'), v('step')), v('count')),), QJump('head')),
            QBlock('exit', (), QReturn(v('count'))),
        ))
        ssa = to_ssa_with_loops(original)
        result = simplify_phis(ssa)
        self.assertEqual(len(result.blocks[1].phis), 1)
        validate_function(result)

    def test_no_phi_is_identity(self):
        fn = QFunction('f', I, (v('x'),), (QBlock('entry', (), QReturn(v('x'))),))
        self.assertEqual(simplify_phis(fn), fn)

if __name__ == '__main__':
    unittest.main()
