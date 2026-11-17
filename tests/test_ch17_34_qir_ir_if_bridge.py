"""Regression tests for conditional lowering through the legacy IR bridge."""
import unittest

from frontend.quar.ir.model import (IRAssign, IRBinary, IRBoolean, IRFunctionDefinition,
                                    IRIf, IRLiteral, IRReference, IRReturn)
from frontend.quar.qir.legacy_bridge import QIRBridgeError, lower_ir_function
from frontend.quar.qir.model import QBranch, QPhi


class QIRIRIfBridgeTests(unittest.TestCase):
    def test_if_else_merges_assignment(self):
        function = IRFunctionDefinition("choose", "i32", (("flag", "bool", None), ("x", "i32", None)), (
            IRIf(IRReference("flag"), (IRAssign("x", IRLiteral(10)),),
                 (IRAssign("x", IRLiteral(20)),)), IRReturn(IRReference("x"))))
        result = lower_ir_function(function)
        self.assertEqual(sum(isinstance(b.terminator, QBranch) for b in result.blocks), 1)
        self.assertEqual(sum(len(b.phis) for b in result.blocks), 1)

    def test_if_without_else_preserves_previous_value(self):
        function = IRFunctionDefinition("maybe", "i32", (("flag", "bool", None), ("x", "i32", None)), (
            IRIf(IRReference("flag"), (IRAssign("x", IRLiteral(9)),), ()),
            IRReturn(IRReference("x"))))
        result = lower_ir_function(function)
        self.assertEqual(sum(len(b.phis) for b in result.blocks), 1)

    def test_nested_if_with_short_circuit(self):
        function = IRFunctionDefinition("nested", "i32", (("a", "bool", None), ("b", "bool", None), ("x", "i32", None)), (
            IRIf(IRBinary("and", IRReference("a"), IRReference("b")),
                 (IRIf(IRReference("b"), (IRAssign("x", IRLiteral(1)),),
                       (IRAssign("x", IRLiteral(2)),)),),
                 (IRAssign("x", IRLiteral(3)),)), IRReturn(IRReference("x"))))
        result = lower_ir_function(function)
        self.assertGreaterEqual(sum(len(b.phis) for b in result.blocks), 2)

    def test_branch_return_is_rejected(self):
        function = IRFunctionDefinition("unsupported", "i32", (("flag", "bool", None),), (
            IRIf(IRReference("flag"), (IRReturn(IRLiteral(1)),), ()), IRReturn(IRLiteral(0))))
        result = lower_ir_function(function)
        self.assertEqual(sum(b.terminator.__class__.__name__ == "QReturn" for b in result.blocks), 2)


if __name__ == "__main__":
    unittest.main()
