"""Chapter 17.6: edge-specific phi nodes and SSA merge validation."""
import unittest

from frontend.quar.qir.model import (
    QBlock, QBranch, QFunction, QInstruction, QJump, QPhi,
    QReturn, QType, QValue,
)
from frontend.quar.qir.validation import QIRValidationError, validate_function

I = QType('i32')
B = QType('bool')
V = QType('void')


def value(name, typ=I):
    return QValue(name, typ)


def diamond(phis):
    return QFunction('choose', I, (value('flag', B), value('x'), value('y')), (
        QBlock('entry', (), QBranch(value('flag', B), 'left', 'right')),
        QBlock('left', (QInstruction('copy', (value('x'),), value('l')),), QJump('merge')),
        QBlock('right', (QInstruction('copy', (value('y'),), value('r')),), QJump('merge')),
        QBlock('merge', (), QReturn(value('out')), phis),
    ))


class TestQIRPhi(unittest.TestCase):
    def test_valid_diamond_merge(self):
        validate_function(diamond((QPhi(value('out'), (('left', value('l')), ('right', value('r')))),)))

    def test_missing_incoming_edge(self):
        with self.assertRaisesRegex(QIRValidationError, 'incoming edges'):
            validate_function(diamond((QPhi(value('out'), (('left', value('l')),)),)))

    def test_duplicate_incoming_edge(self):
        with self.assertRaisesRegex(QIRValidationError, 'incoming edges'):
            validate_function(diamond((QPhi(value('out'), (('left', value('l')), ('left', value('l')))),)))

    def test_unknown_predecessor(self):
        with self.assertRaisesRegex(QIRValidationError, 'incoming edges'):
            validate_function(diamond((QPhi(value('out'), (('left', value('l')), ('ghost', value('r')))),)))

    def test_type_mismatch(self):
        with self.assertRaisesRegex(QIRValidationError, 'phi type mismatch'):
            validate_function(diamond((QPhi(value('out'), (('left', value('l')), ('right', value('flag', B)))),)))

    def test_value_unavailable_on_incoming_edge(self):
        with self.assertRaisesRegex(QIRValidationError, 'undefined value'):
            validate_function(diamond((QPhi(value('out'), (('left', value('r')), ('right', value('l')))),)))

    def test_duplicate_phi_result(self):
        phi = QPhi(value('out'), (('left', value('l')), ('right', value('r'))))
        with self.assertRaisesRegex(QIRValidationError, 'Duplicate'):
            validate_function(diamond((phi, phi)))

    def test_entry_phi_rejected(self):
        function = QFunction('f', V, (value('x'),), (
            QBlock('entry', (), QReturn(), (QPhi(value('z'), (('entry', value('x')),)),)),
        ))
        with self.assertRaisesRegex(QIRValidationError, 'Entry block'):
            validate_function(function)

    def test_loop_carried_value(self):
        function = QFunction('loop', I, (value('start'), value('flag', B)), (
            QBlock('entry', (), QJump('loop')),
            QBlock('loop', (QInstruction('copy', (value('current'),), value('next')),),
                   QBranch(value('flag', B), 'loop', 'exit'),
                   (QPhi(value('current'), (('entry', value('start')), ('loop', value('next')))),)),
            QBlock('exit', (), QReturn(value('current'))),
        ))
        validate_function(function)

    def test_phi_used_in_same_block(self):
        function = diamond((QPhi(value('out'), (('left', value('l')), ('right', value('r')))),))
        validate_function(function)

    def test_duplicate_with_instruction(self):
        function = diamond((QPhi(value('l'), (('left', value('l')), ('right', value('r')))),))
        with self.assertRaisesRegex(QIRValidationError, 'Duplicate'):
            validate_function(function)


if __name__ == '__main__':
    unittest.main()
