"""Tests for conservative backend adapter readiness, not executable backend tests."""
import unittest
from frontend.quar.qir.backend_readiness import inspect_backend_readiness
from frontend.quar.qir.model import (QBlock, QBranch, QFunction, QInstruction,
    QJump, QMetadata, QPhi, QReturn, QSafetyMetadata, QType, QValue)

I = QType("i32")
B = QType("bool")


def function(*instructions, result=None):
    value = result or instructions[-1].result
    return QFunction("f", I, (), (QBlock("entry", tuple(instructions), QReturn(value)),))


class BackendReadinessTests(unittest.TestCase):
    def test_minimal_subset_is_adapter_candidate(self):
        a = QValue("a", I)
        fn = function(QInstruction("const", (), a, 12))
        for backend in ("c", "qrvm"):
            report = inspect_backend_readiness(fn, backend)
            self.assertTrue(report.ready_for_adapter)
            self.assertEqual(report.issues, ())

    def test_unsupported_opcode(self):
        a, b, c = (QValue(x, I) for x in ("a", "b", "c"))
        fn = function(QInstruction("const", (), a, 6), QInstruction("const", (), b, 2),
                      QInstruction("div", (a, b), c))
        self.assertIn("opcode", [x.feature for x in inspect_backend_readiness(fn, "c").issues])

    def test_non_i32_type(self):
        a = QValue("a", QType("i64"))
        fn = QFunction("f", a.type, (), (QBlock("entry", (QInstruction("const", (), a, 1),), QReturn(a)),))
        self.assertIn("type", [x.feature for x in inspect_backend_readiness(fn, "qrvm").issues])

    def test_safety_obligation(self):
        a = QValue("a", I)
        fn = function(QInstruction("const", (), a, 1,
                      QMetadata(safety=QSafetyMetadata(checks=("overflow",)))))
        self.assertIn("safety", [x.feature for x in inspect_backend_readiness(fn, "c").issues])

    def test_branch_and_multiple_blocks(self):
        flag = QValue("flag", B)
        a = QValue("a", I)
        fn = QFunction("f", I, (flag,), (
            QBlock("entry", (), QBranch(flag, "yes", "no")),
            QBlock("yes", (QInstruction("const", (), a, 1),), QReturn(a)),
            QBlock("no", (), QReturn(a))))
        # Invalid QIR must fail validation rather than producing a readiness claim.
        with self.assertRaises(ValueError):
            inspect_backend_readiness(fn, "c")

    def test_valid_multiple_blocks(self):
        a = QValue("a", I)
        fn = QFunction("f", I, (), (
            QBlock("entry", (QInstruction("const", (), a, 1),), QJump("end")),
            QBlock("end", (), QReturn(a))))
        features = {x.feature for x in inspect_backend_readiness(fn, "c").issues}
        self.assertIn("cfg", features)
        self.assertIn("terminator", features)

    def test_unknown_backend(self):
        a = QValue("a", I)
        with self.assertRaises(ValueError):
            inspect_backend_readiness(function(QInstruction("const", (), a, 1)), "llvm")

    def test_does_not_mutate_function(self):
        a = QValue("a", I)
        fn = function(QInstruction("const", (), a, 1))
        before = repr(fn)
        inspect_backend_readiness(fn, "c")
        self.assertEqual(repr(fn), before)


if __name__ == "__main__":
    unittest.main()
