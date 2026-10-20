import unittest
from frontend.quar.ast_nodes import (
    Variable, Integer, BinaryOperation, UnaryOperation, MemberAccess,
)
from frontend.quar.errors import SemanticError
from frontend.quar.semantic import SemanticAnalyzer


class OptionalSafetyGuardsTest(unittest.TestCase):
    def setUp(self):
        self.analyzer = SemanticAnalyzer()
        self.analyzer.variables.update({"maybe": "int?", "value": "int", "flag": "bool?"})

    def test_optional_arithmetic_rejected(self):
        with self.assertRaisesRegex(SemanticError, "Optional values"):
            self.analyzer.analyze_expression(BinaryOperation(Variable("maybe"), "+", Integer(1)))

    def test_optional_comparison_rejected(self):
        with self.assertRaisesRegex(SemanticError, "Optional values"):
            self.analyzer.analyze_expression(BinaryOperation(Variable("maybe"), "==", Integer(1)))

    def test_optional_logical_not_rejected(self):
        with self.assertRaisesRegex(SemanticError, "optional type"):
            self.analyzer.analyze_expression(UnaryOperation("not", Variable("flag")))

    def test_optional_unary_minus_rejected(self):
        with self.assertRaisesRegex(SemanticError, "optional type"):
            self.analyzer.analyze_expression(UnaryOperation("-", Variable("maybe")))

    def test_optional_member_access_rejected(self):
        self.analyzer.variables["widget"] = "Widget?"
        with self.assertRaisesRegex(SemanticError, "optional type"):
            self.analyzer.analyze_expression(MemberAccess("widget", "name"))

    def test_non_optional_arithmetic_unchanged(self):
        self.assertEqual(self.analyzer.analyze_expression(BinaryOperation(Variable("value"), "+", Integer(1))), "i32")

    def test_non_optional_comparison_unchanged(self):
        self.assertEqual(self.analyzer.analyze_expression(BinaryOperation(Variable("value"), "==", Integer(1))), "bool")

    def test_optional_assignment_compatibility_preserved(self):
        self.assertTrue(self.analyzer.types_compatible("int?", "int"))
        self.assertFalse(self.analyzer.types_compatible("int", "int?"))


if __name__ == "__main__":
    unittest.main()
