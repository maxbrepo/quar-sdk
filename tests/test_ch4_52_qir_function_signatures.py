"""Chapter 4.52: strict inter-function signature resolution groundwork."""
import unittest

from frontend.quar.qir.function_signatures import QFunctionSignatures, QIRSignatureError
from frontend.quar.qir.model import QBlock, QFunction, QReturn, QType, QValue


def function(name, parameter_types=("i32",), result_type="i32"):
    parameters = tuple(QValue(f"p{index}", QType(kind)) for index, kind in enumerate(parameter_types))
    return QFunction(name, QType(result_type), parameters,
                     (QBlock("entry", (), QReturn(parameters[0] if parameters else None)),))


class QIRFunctionSignatureTests(unittest.TestCase):
    def test_resolve_exact_integer_signature(self):
        table = QFunctionSignatures((function("helper"), function("caller", ("i32", "i32"))))
        self.assertEqual(table.resolve("helper", (QType("i32"),), QType("i32")).name, "helper")

    def test_reject_unknown_callee(self):
        with self.assertRaisesRegex(QIRSignatureError, "Unknown"):
            QFunctionSignatures((function("helper"),)).resolve("missing", (QType("i32"),), QType("i32"))

    def test_reject_arity_mismatch(self):
        with self.assertRaisesRegex(QIRSignatureError, "argument mismatch"):
            QFunctionSignatures((function("helper"),)).resolve("helper", (), QType("i32"))

    def test_reject_implicit_integer_conversion(self):
        with self.assertRaisesRegex(QIRSignatureError, "argument mismatch"):
            QFunctionSignatures((function("helper"),)).resolve("helper", (QType("i64"),), QType("i32"))

    def test_reject_result_type_mismatch(self):
        with self.assertRaisesRegex(QIRSignatureError, "result mismatch"):
            QFunctionSignatures((function("helper"),)).resolve("helper", (QType("i32"),), QType("i64"))

    def test_reject_duplicate_functions(self):
        with self.assertRaisesRegex(QIRSignatureError, "Duplicate"):
            QFunctionSignatures((function("helper"), function("helper")))

    def test_reject_noncanonical_parameter(self):
        with self.assertRaisesRegex(QIRSignatureError, "Invalid type"):
            QFunctionSignatures((function("helper", ("integer",)),))


if __name__ == "__main__":
    unittest.main()
