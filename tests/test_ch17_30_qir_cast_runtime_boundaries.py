"""Exercise checked QIR integer casts in isolated native processes."""
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from frontend.quar.qir.backend_readiness import inspect_backend_readiness
from frontend.quar.qir.c_backend import QIRCBackendError, emit_c_function
from frontend.quar.qir.model import QBlock, QFunction, QInstruction, QReturn, QType, QValue


def cast_function(source_type: str, target_type: str) -> QFunction:
    source = QValue("source", QType(source_type))
    result = QValue("result", QType(target_type))
    return QFunction("checked_cast", result.type, (source,), (
        QBlock("entry", (QInstruction("cast", (source,), result),), QReturn(result)),
    ))


@unittest.skipUnless(shutil.which("cc"), "C compiler unavailable")
class CheckedCastRuntimeBoundaryTests(unittest.TestCase):
    def run_native(self, source_type: str, target_type: str, value: int) -> subprocess.CompletedProcess:
        function = cast_function(source_type, target_type)
        source = emit_c_function(function)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.c").write_text(
                source + f"\nint main(void) {{ (void)checked_cast({value}); return 0; }}\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "main.c", "-o", "program"],
                cwd=root, capture_output=True, check=True, timeout=15,
            )
            # Disable core dumps so an expected abort does not leave artifacts.
            import resource
            def no_core_dump():
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            return subprocess.run([str(root / "program")], capture_output=True,
                                  timeout=5, preexec_fn=no_core_dump)

    def test_invalid_casts_abort(self):
        for source, target, value in (
            ("i32", "u8", -1), ("i32", "u8", 256),
            ("i32", "i8", -129), ("i32", "i8", 128),
            ("i32", "u16", 65536), ("i16", "u8", -1),
        ):
            with self.subTest(source=source, target=target, value=value):
                result = self.run_native(source, target, value)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.returncode, -6)  # SIGABRT on POSIX.

    def test_boundary_casts_complete(self):
        for source, target, value in (
            ("i32", "u8", 0), ("i32", "u8", 255),
            ("i32", "i8", -128), ("i32", "i8", 127),
            ("i32", "u16", 65535),
        ):
            with self.subTest(source=source, target=target, value=value):
                self.assertEqual(self.run_native(source, target, value).returncode, 0)

    def test_non_i32_arithmetic_is_rejected(self):
        left = QValue("left", QType("u8"))
        right = QValue("right", QType("u8"))
        result = QValue("result", QType("u8"))
        function = QFunction("unsupported_add", result.type, (left, right), (
            QBlock("entry", (QInstruction("add", (left, right), result),), QReturn(result)),
        ))
        report = inspect_backend_readiness(function, "c")
        self.assertFalse(report.ready_for_adapter)
        with self.assertRaises(QIRCBackendError):
            emit_c_function(function)


if __name__ == "__main__":
    unittest.main()
