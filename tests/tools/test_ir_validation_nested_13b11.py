"""Regression checks for symbol validation in nested Quar IR nodes."""
import unittest

from frontend.quar.ir.model import (IRBinary, IRCall, IRFunction, IRIf,
    IRLiteral, IRModule, IRProject, IRTryCatch, IRWhile)
from frontend.quar.ir.validation import IRValidationError, validate_project


class NestedIRValidationTests(unittest.TestCase):
    def project(self, statement):
        return IRProject((IRModule('main.vq', (), (
            IRFunction('main.vq::main', 'int', (), (statement,)),
            IRFunction('main.vq::known', 'int', (), ()),
        )),))

    def test_rejects_unknown_call_in_nested_loop_condition(self):
        statement = IRIf(IRLiteral(1), (
            IRWhile(IRBinary('<', IRCall('main.vq::missing', ()), IRLiteral(3)), ()),
        ), ())
        with self.assertRaisesRegex(IRValidationError, 'main.vq::missing'):
            validate_project(self.project(statement))

    def test_rejects_unknown_call_in_catch_body(self):
        statement = IRTryCatch((), 'error', (IRCall('main.vq::missing', ()),))
        with self.assertRaises(IRValidationError):
            validate_project(self.project(statement))

    def test_accepts_known_call_in_nested_structure(self):
        statement = IRIf(IRLiteral(1), (IRWhile(IRLiteral(0), (
            IRCall('main.vq::known', ()),
        )),), ())
        validate_project(self.project(statement))


if __name__ == '__main__':
    unittest.main()
