"""Chapter 17.11: cross-block SSA integer constant propagation."""
import unittest
from frontend.quar.qir.global_constants import propagate_integer_constants
from frontend.quar.qir.model import QBlock, QBranch, QFunction, QInstruction, QJump, QPhi, QReturn, QType, QValue

I32 = QType("i32")
BOOL = QType("bool")
def v(name, typ=I32):
    return QValue(name, typ)
def const(name, number):
    return QInstruction("const", (), v(name), number)
def run(blocks, params=()):
    return propagate_integer_constants(QFunction("f", I32, params, tuple(blocks)))

class TestGlobalConstants(unittest.TestCase):
    def test_cross_block_add(self):
        blocks = (QBlock("entry", (const("a", 12),), QJump("end")),
                  QBlock("end", (const("b", 30), QInstruction("add", (v("a"), v("b")), v("out"))), QReturn(v("out"))))
        self.assertEqual(run(blocks).blocks[1].instructions[-1].immediate, 42)

    def test_diamond_equal_phi(self):
        blocks = (QBlock("entry", (), QBranch(v("flag", BOOL), "left", "right")),
                  QBlock("left", (const("a", 7),), QJump("merge")),
                  QBlock("right", (const("b", 7),), QJump("merge")),
                  QBlock("merge", (QInstruction("copy", (v("merged"),), v("out")),), QReturn(v("out")),
                         (QPhi(v("merged"), (("left", v("a")), ("right", v("b")))),)))
        self.assertEqual(run(blocks, (v("flag", BOOL),)).blocks[-1].instructions[0].immediate, 7)

    def test_diamond_different_phi_not_folded(self):
        blocks = (QBlock("entry", (), QBranch(v("flag", BOOL), "left", "right")),
                  QBlock("left", (const("a", 7),), QJump("merge")),
                  QBlock("right", (const("b", 8),), QJump("merge")),
                  QBlock("merge", (QInstruction("copy", (v("merged"),), v("out")),), QReturn(v("out")),
                         (QPhi(v("merged"), (("left", v("a")), ("right", v("b")))),)))
        self.assertEqual(run(blocks, (v("flag", BOOL),)).blocks[-1].instructions[0].opcode, "copy")

    def test_unknown_parameter(self):
        blocks = (QBlock("entry", (const("a", 2),), QJump("end")),
                  QBlock("end", (QInstruction("add", (v("a"), v("x")), v("out")),), QReturn(v("out"))))
        self.assertEqual(run(blocks, (v("x"),)).blocks[-1].instructions[0].opcode, "add")

    def test_overflow_unchanged(self):
        t = QType("u8")
        a, b, out = v("a", t), v("b", t), v("out", t)
        blocks = (QBlock("entry", (QInstruction("const", (), a, 255),), QJump("end")),
                  QBlock("end", (QInstruction("const", (), b, 1), QInstruction("add", (a, b), out)), QReturn(out)))
        f = QFunction("f", t, (), blocks)
        self.assertEqual(propagate_integer_constants(f).blocks[-1].instructions[-1].opcode, "add")

    def test_loop_carried_unknown(self):
        blocks = (QBlock("entry", (const("start", 0),), QJump("loop")),
                  QBlock("loop", (QInstruction("add", (v("current"), v("one")), v("next")),),
                         QBranch(v("flag", BOOL), "loop", "exit"),
                         (QPhi(v("current"), (("entry", v("start")), ("loop", v("next")))),)),
                  QBlock("exit", (QInstruction("copy", (v("current"),), v("out")),), QReturn(v("out"))))
        # 'one' is a parameter: no value can be assumed for the loop-carried phi.
        self.assertEqual(run(blocks, (v("one"), v("flag", BOOL))).blocks[-1].instructions[0].opcode, "copy")

    def test_original_unchanged_and_idempotent(self):
        blocks = (QBlock("entry", (const("a", 2),), QJump("end")),
                  QBlock("end", (QInstruction("copy", (v("a"),), v("out")),), QReturn(v("out"))))
        original = QFunction("f", I32, (), blocks)
        first = propagate_integer_constants(original)
        self.assertEqual(original.blocks[-1].instructions[0].opcode, "copy")
        self.assertEqual(first, propagate_integer_constants(first))

if __name__ == "__main__":
    unittest.main()
