"""Chapter 17.12: conservative dead-code elimination regression tests."""
import unittest
from frontend.quar.qir.model import QType, QValue, QInstruction, QBlock, QFunction, QReturn, QJump, QBranch
from frontend.quar.qir.dead_code import eliminate_dead_results
from frontend.quar.qir.validation import validate_function

I32 = QType("i32")
BOOL = QType("bool")
VOID = QType("void")


def fn(instructions, term=None, parameters=(), return_type=VOID):
    return QFunction("f", return_type, parameters, (QBlock("entry", tuple(instructions), term or QReturn()),))


class TestDeadCode(unittest.TestCase):
    def test_unused_constant_removed(self):
        x = QValue("x", I32)
        original = fn((QInstruction("const", (), x, 7),))
        optimized = eliminate_dead_results(original)
        self.assertEqual(optimized.blocks[0].instructions, ())
        self.assertEqual(len(original.blocks[0].instructions), 1)

    def test_live_return_kept(self):
        x = QValue("x", I32)
        original = fn((QInstruction("const", (), x, 7),), QReturn(x), return_type=I32)
        self.assertEqual(eliminate_dead_results(original), original)

    def test_transitive_dead_chain(self):
        x, y = QValue("x", I32), QValue("y", I32)
        original = fn((QInstruction("const", (), x, 7), QInstruction("copy", (x,), y)))
        self.assertEqual(eliminate_dead_results(original).blocks[0].instructions, ())

    def test_arithmetic_preserved_when_dead(self):
        x, y, z = (QValue(n, I32) for n in ("x", "y", "z"))
        original = fn((QInstruction("add", (x, y), z),), parameters=(x, y))
        self.assertEqual(eliminate_dead_results(original), original)

    def test_store_preserved(self):
        p, x = QValue("p", QType("ptr<i32>")), QValue("x", I32)
        original = fn((QInstruction("store", (p, x)),), parameters=(p, x))
        self.assertEqual(eliminate_dead_results(original), original)

    def test_branch_condition_kept(self):
        flag = QValue("flag", BOOL)
        original = QFunction("f", VOID, (), (
            QBlock("entry", (QInstruction("eq", (QValue("a", I32), QValue("b", I32)), flag),), QBranch(flag, "yes", "no")),
            QBlock("yes", (), QReturn()), QBlock("no", (), QReturn()),
        ))
        # The operands are supplied as parameters to keep the graph valid.
        original = replace_function_parameters(original, (QValue("a", I32), QValue("b", I32)))
        self.assertEqual(eliminate_dead_results(original), original)

    def test_idempotent(self):
        x = QValue("x", I32)
        original = fn((QInstruction("const", (), x, 3),))
        once = eliminate_dead_results(original)
        self.assertEqual(eliminate_dead_results(once), once)


def replace_function_parameters(function, parameters):
    from dataclasses import replace
    return replace(function, parameters=parameters)

if __name__ == "__main__":
    unittest.main()
