"""Conservative checks for the QIR-to-production migration decision."""
import unittest
from frontend.quar.qir.migration_gate import (MigrationEvidence, inspect_migration_gate)
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QReturn, QType, QValue


def sample():
    value = QValue("v", QType("i32"))
    return QFunction("f", value.type, (), (
        QBlock("entry", (QInstruction("const", (), value, 42),), QReturn(value)),))


class MigrationGateTests(unittest.TestCase):
    def test_default_blocks_removal(self):
        report = inspect_migration_gate((sample(),))
        self.assertFalse(report.can_remove_legacy_ir)
        self.assertEqual(report.inspected_functions, 1)
        self.assertEqual(len(report.blockers), 9)

    def test_missing_inferred_and_mixed_are_named(self):
        report = inspect_migration_gate((sample(),), MigrationEvidence(typed_verified=True))
        self.assertIn("missing evidence: inferred_verified", report.blockers)
        self.assertIn("missing evidence: mixed_verified", report.blockers)

    def test_empty_sample_never_authorizes_removal(self):
        evidence = MigrationEvidence(**{key: True for key in MigrationEvidence.__dataclass_fields__})
        report = inspect_migration_gate((), evidence)
        self.assertFalse(report.can_remove_legacy_ir)
        self.assertIn("no QIR functions supplied for audit", report.blockers)

    def test_unsupported_operation_is_reported(self):
        value = QValue("v", QType("i64"))
        fn = QFunction("f", value.type, (), (
            QBlock("entry", (QInstruction("const", (), value, 2),), QReturn(value)),))
        report = inspect_migration_gate((fn,))
        self.assertTrue(any("Unsupported adapter type" in x for x in report.blockers))

    def test_invalid_qir_is_rejected(self):
        value = QValue("v", QType("i32"))
        fn = QFunction("f", value.type, (), (QBlock("entry", (), QReturn(value)),))
        with self.assertRaises(ValueError):
            inspect_migration_gate((fn,))

    def test_multiple_functions_counted(self):
        report = inspect_migration_gate((sample(), sample()))
        self.assertEqual(report.inspected_functions, 2)

    def test_explicit_all_green_is_only_a_declaration(self):
        evidence = MigrationEvidence(**{key: True for key in MigrationEvidence.__dataclass_fields__})
        report = inspect_migration_gate((sample(),), evidence)
        self.assertTrue(report.can_remove_legacy_ir)
        # The caller is responsible for verifying evidence independently.

    def test_evidence_is_immutable(self):
        evidence = MigrationEvidence()
        with self.assertRaises(AttributeError):
            evidence.typed_verified = True


if __name__ == "__main__":
    unittest.main()
