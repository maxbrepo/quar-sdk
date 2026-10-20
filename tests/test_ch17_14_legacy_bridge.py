"""Opt-in legacy IR to QIR bridge regression tests."""
import unittest
from frontend.quar.ir.model import (IRAssign, IRBinary, IRDeclare,
    IRFunctionDefinition, IRIf, IRLiteral, IRReference, IRReturn)
from frontend.quar.qir.legacy_bridge import lower_ir_function, QIRBridgeError
from frontend.quar.qir.validation import validate_function


class LegacyBridgeTests(unittest.TestCase):
    def function(self, body, parameters=(), return_type="i32"):
        return IRFunctionDefinition("compute", return_type, parameters, body)

    def test_integer_literal(self):
        result = lower_ir_function(self.function((IRReturn(IRLiteral(42)),)))
        validate_function(result)
        self.assertEqual(result.blocks[0].instructions[0].immediate, 42)

    def test_parameter_and_arithmetic(self):
        function = self.function((IRReturn(IRBinary("+", IRReference("x"), IRLiteral(3))),),
                                 (("x", "i32", None),))
        result = lower_ir_function(function)
        self.assertEqual(result.blocks[0].instructions[-1].opcode, "add")
        validate_function(result)

    def test_assignment_renames_values(self):
        function = self.function((IRDeclare("x", "i32", IRLiteral(1)),
            IRAssign("x", IRBinary("+", IRReference("x"), IRLiteral(2))),
            IRReturn(IRReference("x"))))
        result = lower_ir_function(function)
        self.assertEqual(result.blocks[0].terminator.value,
                         result.blocks[0].instructions[-1].result)
        validate_function(result)

    def test_original_ir_unchanged(self):
        function = self.function((IRReturn(IRLiteral(1)),))
        lower_ir_function(function)
        self.assertEqual(function.body[0].value.value, 1)

    def test_reject_unsupported_control_flow(self):
        function = self.function((IRIf(IRLiteral(1), (), ()), IRReturn(IRLiteral(0))))
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(function)

    def test_reject_implicit_conversion(self):
        function = self.function((IRReturn(IRReference("x")),), (("x", "i64", None),))
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(function)

    def test_reject_unknown_reference(self):
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(self.function((IRReturn(IRReference("missing")),)))

    def test_reject_default_parameters(self):
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(self.function((IRReturn(IRLiteral(1)),), (("x", "i32", IRLiteral(1)),)))

    def test_reject_out_of_range_constant(self):
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(self.function((IRReturn(IRLiteral(256)),), return_type="u8"))

    def test_reject_missing_return(self):
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(self.function((IRDeclare("x", "i32", IRLiteral(1)),)))

    def test_reject_unsupported_type(self):
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(self.function((IRReturn(IRLiteral(1)),), return_type="unknown_type"))

    def test_reject_statements_after_return(self):
        with self.assertRaises(QIRBridgeError):
            lower_ir_function(self.function((IRReturn(IRLiteral(1)), IRReturn(IRLiteral(2)))))


if __name__ == "__main__":
    unittest.main()
