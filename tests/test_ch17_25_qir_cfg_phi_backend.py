"""Executable QIR CFG regression tests for edge-specific parallel phi copies."""
import unittest
from frontend.quar.qir.model import QBlock, QBranch, QFunction, QInstruction, QJump, QPhi, QReturn, QType, QValue
from tests.test_ch17_18_qir_c_backend import CBackendTests

I = QType('i32')
B = QType('bool')

class CFGBackendTests(CBackendTests):
    def test_branch_phi(self):
        cond = QValue('cond', B)
        a, b, out = (QValue(x, I) for x in ('a', 'b', 'out'))
        fn = QFunction('qir_branch', I, (cond,), (
            QBlock('entry', (), QBranch(cond, 'yes', 'no')),
            QBlock('yes', (QInstruction('const', (), a, 11),), QJump('merge')),
            QBlock('no', (QInstruction('const', (), b, 22),), QJump('merge')),
            QBlock('merge', (), QReturn(out), (QPhi(out, (('yes', a), ('no', b))),)),
        ))
        self.assertEqual(self.run_c(fn, (1,)), 11)
        self.assertEqual(self.run_c(fn, (0,)), 22)

    def test_phi_parallel_swap_loop(self):
        n = QValue('n', I)
        zero, one, eleven, twenty_two = (QValue(x, I) for x in ('zero', 'one', 'eleven', 'twenty_two'))
        i, a, b = (QValue(x, I) for x in ('i', 'a', 'b'))
        next_i, more = QValue('next_i', I), QValue('more', B)
        fn = QFunction('qir_swap', I, (n,), (
            QBlock('entry', (QInstruction('const', (), zero, 0), QInstruction('const', (), one, 1),
                             QInstruction('const', (), eleven, 11), QInstruction('const', (), twenty_two, 22)), QJump('head')),
            QBlock('head', (QInstruction('lt', (i, n), more),), QBranch(more, 'body', 'exit'), (
                QPhi(i, (('entry', zero), ('body', next_i))),
                QPhi(a, (('entry', eleven), ('body', b))),
                QPhi(b, (('entry', twenty_two), ('body', a))),
            )),
            QBlock('body', (QInstruction('add', (i, one), next_i),), QJump('head')),
            QBlock('exit', (), QReturn(a)),
        ))
        for count, expected in ((0, 11), (1, 22), (2, 11), (3, 22)):
            with self.subTest(count=count):
                self.assertEqual(self.run_c(fn, (count,)), expected)
