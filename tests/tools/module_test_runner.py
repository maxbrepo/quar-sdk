from pathlib import Path

from frontend.quar.module_loader import ModuleLoader, ModuleLoadError
from frontend.quar.semantic import SemanticAnalyzer
from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


EXPECTED_ERRORS = {
    46: "Duplicate import:",
    47: "Module not found:",
    48: "Circular module dependency:",
}


def run_test(source_file, project_root):
    test_number = int(source_file.name.split(" ", 1)[0])

    try:
        program = ModuleLoader(project_root).load(source_file)
        validated = SemanticAnalyzer().analyze(program)
        instructions = QRVMCompiler().compile(validated)
        QRVM().run(instructions)
    except ModuleLoadError as error:
        expected = EXPECTED_ERRORS.get(test_number)
        if expected is not None and str(error).startswith(expected):
            return True, f"expected error: {error}"
        return False, str(error)

    if test_number in EXPECTED_ERRORS:
        return False, "expected module error was not raised"

    return True, "ok"
    # Return regression test result


def main():
    project_root = Path.cwd()

    for test_number in range(41, 49):
        matches = sorted(project_root.glob(f"{test_number} *.vq"))
        if len(matches) != 1:
            print(f"{test_number}: FAIL - test source not found")
            continue

        passed, detail = run_test(matches[0], project_root)
        status = "PASS" if passed else "FAIL"
        print(f"{test_number}: {status} - {detail}")


if __name__ == "__main__":
    main()
