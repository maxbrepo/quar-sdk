"""Executable CFG and phi tests for the experimental QIR C adapter."""
import ctypes
import os
import shutil
import subprocess
import tempfile
import unittest

from frontend.quar.qir.c_backend import emit_c_function
from frontend.quar.qir.model import (
    QBlock, QBranch, QFunction, QInstruction, QJump, QPhi,
    QReturn, QType, QValue,
)

I = QType("i32")
B = QType("bool")


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class CFGCBackendTests(unittest.TestCase):
    def compile_and_run(self, function, *args):
        """Compile QIR-generated C and return its i32 result."""
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "program.c")
            shared = os.path.join(directory, "program.so")
            with open(source, "w", encoding="utf-8") as stream:
                stream.write(emit_c_function(function))
            subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", source, "-o", shared],
                           capture_output=True, check=True)
            call = getattr(ctypes.CDLL(shared), function.name)
            call.argtypes = [ctypes.c_int32] * len(args)
            call.restype = ctypes.c_int32
            return call(*args)

    def test_branch_and_phi_choose_correct_predecessor(self):
        """A phi selects the value produced by the executed branch."""
        flag, yes, no, merged = (QValue("flag", B), QValue("yes", I), QValue("no", I), QValue("merged", I))
        fn = QFunction("branch_phi", I, (flag,), (
            QBlock("entry", (), QBranch(flag, "then", "else")),
            QBlock("then", (QInstruction("const", (), yes, 11),), QJump("join")),
            QBlock("else", (QInstruction("const", (), no, 22),), QJump("join")),
            QBlock("join", (), QReturn(merged), (QPhi(merged, (("then", yes), ("else", no))),)),
        ))
        self.assertEqual(self.compile_and_run(fn, 1), 11)
        self.assertEqual(self.compile_and_run(fn, 0), 22)

    def test_skipped_branch_does_not_divide_by_zero(self):
        """An untaken branch must not evaluate its potentially trapping RHS."""
        flag, one, zero, unsafe, safe, merged = (
            QValue("flag", B), QValue("one", I), QValue("zero", I),
            QValue("unsafe", I), QValue("safe", I), QValue("merged", I),
        )
        fn = QFunction("skip_rhs", I, (flag,), (
            QBlock("entry", (), QBranch(flag, "safe_block", "unsafe_block")),
            QBlock("safe_block", (QInstruction("const", (), safe, 7),), QJump("join")),
            QBlock("unsafe_block", (QInstruction("const", (), one, 1),
                                     QInstruction("const", (), zero, 0),
                                     QInstruction("div", (one, zero), unsafe)), QJump("join")),
            QBlock("join", (), QReturn(merged), (QPhi(merged, (("safe_block", safe), ("unsafe_block", unsafe))),)),
        ))
        self.assertEqual(self.compile_and_run(fn, 1), 7)

    def test_loop_phi_updates_are_simultaneous(self):
        """A loop back edge must swap phi values without overwriting an input."""
        a0, b0, n0 = (QValue("a0", I), QValue("b0", I), QValue("n0", I))
        a, b, n = (QValue("a", I), QValue("b", I), QValue("n", I))
        one, next_n, zero, keep_going = (
            QValue("one", I), QValue("next_n", I), QValue("zero", I), QValue("keep_going", B)
        )
        fn = QFunction("phi_swap_loop", I, (a0, b0, n0), (
            QBlock("entry", (), QJump("loop")),
            QBlock("loop", (
                QInstruction("const", (), one, 1),
                QInstruction("const", (), zero, 0),
                QInstruction("gt", (n, zero), keep_going),
            ), QBranch(keep_going, "body", "exit"), (
                QPhi(a, (("entry", a0), ("body", b))),
                QPhi(b, (("entry", b0), ("body", a))),
                QPhi(n, (("entry", n0), ("body", next_n))),
            )),
            QBlock("body", (QInstruction("sub", (n, one), next_n),), QJump("loop")),
            QBlock("exit", (), QReturn(a)),
        ))
        self.assertEqual(self.compile_and_run(fn, 11, 22, 0), 11)
        self.assertEqual(self.compile_and_run(fn, 11, 22, 1), 22)
        self.assertEqual(self.compile_and_run(fn, 11, 22, 2), 11)
        self.assertEqual(self.compile_and_run(fn, 11, 22, 3), 22)
