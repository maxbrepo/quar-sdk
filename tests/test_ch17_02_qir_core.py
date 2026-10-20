"""Chapter 17.2: canonical QIR graph invariants."""
import unittest
from frontend.quar.qir.model import QType, QValue, QInstruction, QReturn, QJump, QBranch, QBlock, QFunction, QModule
from frontend.quar.qir.validation import QIRValidationError, validate_function, validate_module

I32 = QType("i32")
BOOL = QType("bool")
VOID = QType("void")

class TestQIRCore(unittest.TestCase):
    def test_single_block(self):
        value = QValue("x", I32)
        function = QFunction("identity", I32, (value,), (QBlock("entry", (), QReturn(value)),))
        validate_module(QModule("main", (function,)))

    def test_control_flow(self):
        flag = QValue("flag", BOOL)
        function = QFunction("choice", VOID, (flag,), (
            QBlock("entry", (), QBranch(flag, "yes", "no")),
            QBlock("yes", (), QJump("exit")),
            QBlock("no", (), QJump("exit")),
            QBlock("exit", (), QReturn()),
        ))
        validate_function(function)

    def test_duplicate_blocks(self):
        function = QFunction("f", VOID, (), (QBlock("x", (), QReturn()), QBlock("x", (), QReturn())))
        with self.assertRaises(QIRValidationError):
            validate_function(function)

    def test_missing_target(self):
        function = QFunction("f", VOID, (), (QBlock("entry", (), QJump("missing")),))
        with self.assertRaises(QIRValidationError):
            validate_function(function)

    def test_branch_type(self):
        function = QFunction("f", VOID, (), (QBlock("entry", (), QBranch(QValue("n", I32), "entry", "entry")),))
        with self.assertRaises(QIRValidationError):
            validate_function(function)

    def test_return_type(self):
        function = QFunction("f", I32, (), (QBlock("entry", (), QReturn()),))
        with self.assertRaises(QIRValidationError):
            validate_function(function)

    def test_duplicate_functions(self):
        function = QFunction("f", VOID, (), (QBlock("entry", (), QReturn()),))
        with self.assertRaises(QIRValidationError):
            validate_module(QModule("m", (function, function)))

if __name__ == "__main__":
    unittest.main()
