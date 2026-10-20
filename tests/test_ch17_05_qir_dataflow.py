"""Chapter 17.5: QIR must-defined values and control flow."""
import unittest
from frontend.quar.qir.model import QType, QValue, QInstruction, QReturn, QJump, QBranch, QBlock, QFunction
from frontend.quar.qir.validation import QIRValidationError, validate_function

I = QType("i32")
B = QType("bool")
V = QType("void")

def val(name, typ=I):
    return QValue(name, typ)

class TestQIRDataflow(unittest.TestCase):
    def check(self, blocks, params=(), ret=V):
        validate_function(QFunction("f", ret, params, blocks))

    def test_parameter_return(self):
        self.check((QBlock("entry", (), QReturn(val("x"))),), (val("x"),), I)

    def test_undefined_return(self):
        with self.assertRaisesRegex(QIRValidationError, "undefined value"):
            self.check((QBlock("entry", (), QReturn(val("missing"))),), ret=I)

    def test_undefined_operand(self):
        instruction = QInstruction("copy", (val("missing"),), val("out"))
        with self.assertRaisesRegex(QIRValidationError, "undefined value"):
            self.check((QBlock("entry", (instruction,), QReturn()),))

    def test_definition_before_use(self):
        instructions = (QInstruction("copy", (val("x"),), val("y")),
                        QInstruction("add", (val("y"), val("x")), val("z")))
        self.check((QBlock("entry", instructions, QReturn(val("z"))),), (val("x"),), I)

    def test_use_before_definition(self):
        instructions = (QInstruction("copy", (val("y"),), val("z")),
                        QInstruction("copy", (val("x"),), val("y")))
        with self.assertRaisesRegex(QIRValidationError, "undefined value"):
            self.check((QBlock("entry", instructions, QReturn()),), (val("x"),))

    def test_branch_missing_path(self):
        blocks = (QBlock("entry", (), QBranch(val("flag", B), "left", "right")),
                  QBlock("left", (QInstruction("copy", (val("x"),), val("y")),), QJump("exit")),
                  QBlock("right", (), QJump("exit")),
                  QBlock("exit", (QInstruction("copy", (val("y"),), val("z")),), QReturn()))
        with self.assertRaisesRegex(QIRValidationError, "undefined value"):
            self.check(blocks, (val("flag", B), val("x")))

    def test_branch_all_paths_parameter(self):
        blocks = (QBlock("entry", (), QBranch(val("flag", B), "left", "right")),
                  QBlock("left", (), QJump("exit")),
                  QBlock("right", (), QJump("exit")),
                  QBlock("exit", (QInstruction("copy", (val("x"),), val("z")),), QReturn()))
        self.check(blocks, (val("flag", B), val("x")))

    def test_loop_backedge(self):
        blocks = (QBlock("entry", (), QJump("loop")),
                  QBlock("loop", (), QBranch(val("flag", B), "loop", "exit")),
                  QBlock("exit", (), QReturn()))
        self.check(blocks, (val("flag", B),))

    def test_duplicate_definition(self):
        blocks = (QBlock("entry", (QInstruction("copy", (val("x"),), val("x")),), QReturn()),)
        with self.assertRaisesRegex(QIRValidationError, "Duplicate"):
            self.check(blocks, (val("x"),))

    def test_type_mismatch_same_name(self):
        blocks = (QBlock("entry", (QInstruction("copy", (val("x", I),), val("y", I)),),
                         QReturn(val("y", B))),)
        with self.assertRaises(QIRValidationError):
            self.check(blocks, (val("x"),), B)

    def test_unreachable_block_not_analyzed_for_use(self):
        blocks = (QBlock("entry", (), QReturn()),
                  QBlock("dead", (QInstruction("copy", (val("missing"),), val("z")),), QReturn()))
        self.check(blocks)

if __name__ == "__main__":
    unittest.main()
