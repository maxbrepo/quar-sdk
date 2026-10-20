import unittest
from frontend.quar.ir import (lower_function_body, UnsupportedIRNode, IRReturn,
                              IRBinary, IRLiteral, IRCall, lower_executable_project)
from frontend.quar.ast_nodes import (FunctionDefinition, FunctionCall, ReturnStatement,
                                     BinaryOperation, Integer, ClassDefinition)

class IR13A15Tests(unittest.TestCase):
    def test_arithmetic_return(self):
        fn = FunctionDefinition("int", "answer", [], [
            ReturnStatement(BinaryOperation(Integer(40), "+", Integer(2)))])
        self.assertEqual(lower_function_body(fn),
                         (IRReturn(IRBinary("+", IRLiteral(40), IRLiteral(2))),))

    def test_call_return(self):
        fn = FunctionDefinition("int", "use", [], [
            ReturnStatement(FunctionCall("shared.answer", [Integer(3)]))])
        self.assertEqual(lower_function_body(fn),
                         (IRReturn(IRCall("shared.answer", (IRLiteral(3),))),))

    def test_class_definition_is_supported(self):
        fn = FunctionDefinition("int", "f", [], [
            ClassDefinition("Sample", [], None, [])])
        self.assertEqual(lower_function_body(fn)[0].name, "Sample")

if __name__ == "__main__":
    unittest.main()
