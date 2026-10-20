"""Chapter 17.8: loop-carried SSA construction and safety cases."""
import unittest
from frontend.quar.qir.model import QBlock, QBranch, QFunction, QInstruction, QJump, QReturn, QType, QValue
from frontend.quar.qir.ssa_loops import to_ssa_with_loops
from frontend.quar.qir.ssa import QIRSSAError
from frontend.quar.qir.validation import validate_function
I = QType('i32')
B = QType('bool')
def v(name, typ=I):
    return QValue(name, typ)

class TestSSALoops(unittest.TestCase):
    def loop(self):
        return QFunction('counter', I, (v('initial'), v('step'), v('condition', B)), (
            QBlock('entry', (QInstruction('copy', (v('initial'),), v('counter')),), QJump('header')),
            QBlock('header', (), QBranch(v('condition', B), 'body', 'exit')),
            QBlock('body', (QInstruction('add', (v('counter'), v('step')), v('counter')),), QJump('header')),
            QBlock('exit', (), QReturn(v('counter'))),
        ))
    def test_loop_phi(self):
        result = to_ssa_with_loops(self.loop())
        validate_function(result)
        header = result.blocks[1]
        self.assertEqual(len(header.phis), 1)
        self.assertEqual({p for p, _ in header.phis[0].incoming}, {'entry', 'body'})
        self.assertEqual(result.blocks[2].instructions[0].operands[0], header.phis[0].result)
        self.assertEqual(result.blocks[3].terminator.value, header.phis[0].result)
    def test_input_unchanged(self):
        original = self.loop()
        to_ssa_with_loops(original)
        self.assertEqual(original.blocks[1].phis, ())
    def test_acyclic_compatibility(self):
        fn = QFunction('f', I, (v('x'),), (QBlock('entry', (), QReturn(v('x'))),))
        validate_function(to_ssa_with_loops(fn))
    def test_missing_initial_definition(self):
        original = self.loop()
        blocks = list(original.blocks)
        blocks[0] = QBlock('entry', (), QJump('header'))
        with self.assertRaises(QIRSSAError):
            to_ssa_with_loops(QFunction(original.name, original.return_type, original.parameters, tuple(blocks)))
    def test_unreachable_rejected(self):
        original = self.loop()
        blocks = original.blocks + (QBlock('dead', (), QReturn(v('initial'))),)
        with self.assertRaisesRegex(QIRSSAError, 'Unreachable'):
            to_ssa_with_loops(QFunction(original.name, original.return_type, original.parameters, blocks))
    def test_existing_phi_rejected(self):
        original = self.loop()
        converted = to_ssa_with_loops(original)
        with self.assertRaisesRegex(QIRSSAError, 'Preexisting'):
            to_ssa_with_loops(converted)

if __name__ == '__main__':
    unittest.main()
