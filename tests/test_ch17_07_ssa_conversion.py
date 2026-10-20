"""Chapter 17.7: automatic SSA for acyclic control-flow graphs."""
import unittest
from frontend.quar.qir.model import QBlock, QBranch, QFunction, QInstruction, QJump, QReturn, QType, QValue
from frontend.quar.qir.ssa import QIRSSAError, to_ssa
from frontend.quar.qir.validation import validate_function

I = QType('i32')
B = QType('bool')

def v(name, typ=I):
    return QValue(name, typ)

class TestSSAConversion(unittest.TestCase):
    def diamond(self):
        return QFunction('choose', I, (v('flag', B), v('x'), v('y')), (
            QBlock('entry', (), QBranch(v('flag', B), 'left', 'right')),
            QBlock('left', (QInstruction('copy', (v('x'),), v('out')),), QJump('merge')),
            QBlock('right', (QInstruction('copy', (v('y'),), v('out')),), QJump('merge')),
            QBlock('merge', (), QReturn(v('out'))),
        ))

    def test_diamond_phi(self):
        original = self.diamond()
        converted = to_ssa(original)
        validate_function(converted)
        phi = converted.blocks[3].phis[0]
        self.assertEqual({p for p, _ in phi.incoming}, {'left', 'right'})
        self.assertEqual(converted.blocks[3].terminator.value, phi.result)
        self.assertEqual(original.blocks[3].phis, ())

    def test_linear_reassignment(self):
        fn = QFunction('f', I, (v('x'),), (QBlock('entry', (
            QInstruction('copy', (v('x'),), v('a')),
            QInstruction('copy', (v('a'),), v('a')),
        ), QReturn(v('a'))),))
        converted = to_ssa(fn)
        self.assertNotEqual(converted.blocks[0].instructions[0].result.name,
                            converted.blocks[0].instructions[1].result.name)
        validate_function(converted)

    def test_undefined_join(self):
        fn = self.diamond()
        right = QBlock('right', (), QJump('merge'))
        with self.assertRaisesRegex(QIRSSAError, 'Undefined return'):
            to_ssa(QFunction(fn.name, fn.return_type, fn.parameters,
                             (fn.blocks[0], fn.blocks[1], right, fn.blocks[3])))

    def test_loop_rejected(self):
        fn = QFunction('loop', I, (v('x'),), (
            QBlock('entry', (), QJump('loop')),
            QBlock('loop', (), QBranch(v('x', B), 'loop', 'exit')),
            QBlock('exit', (), QReturn(v('x'))),
        ))
        with self.assertRaisesRegex(QIRSSAError, 'Loops'):
            to_ssa(fn)

    def test_type_conflict(self):
        fn = self.diamond()
        right = QBlock('right', (QInstruction('copy', (v('flag', B),), v('out', B)),), QJump('merge'))
        with self.assertRaisesRegex(QIRSSAError, 'Conflicting types'):
            to_ssa(QFunction(fn.name, fn.return_type, fn.parameters,
                             (fn.blocks[0], fn.blocks[1], right, fn.blocks[3])))

    def test_undefined_operand(self):
        fn = QFunction('f', I, (), (QBlock('entry',
            (QInstruction('copy', (v('missing'),), v('out')),), QReturn(v('out'))),))
        with self.assertRaisesRegex(QIRSSAError, 'Undefined or mismatched'):
            to_ssa(fn)

    def test_duplicate_target_edges(self):
        fn = QFunction('f', I, (v('flag', B), v('x')), (
            QBlock('entry', (), QBranch(v('flag', B), 'join', 'join')),
            QBlock('join', (), QReturn(v('x'))),
        ))
        validate_function(to_ssa(fn))

if __name__ == '__main__':
    unittest.main()
