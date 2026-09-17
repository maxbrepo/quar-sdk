import platform
import shutil
import subprocess
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer

from frontend.quar.errors import (
    LexerError,
    ParserError,
    SemanticError,
)

from backend.c.codegen import CCodeGenerator

from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM


def select_execution_mode():
    print("Execution mode:")
    print("(a) Interpreted")
    print("(b) Compiled")

    choice = input("> ").strip().lower()

    if choice not in ("a", "b"):
        raise ValueError(
            "Invalid execution mode"
        )

    return choice
    # Return selected execution mode


def detect_host():
    system = platform.system().lower()

    if system == "linux":
        return "linux"

    if system == "windows":
        return "windows"

    if system == "darwin":
        return "macos"

    return "unknown"
    # Return current host platform


def select_target_platform(host):
    targets = []

    if host == "linux":
        if shutil.which("gcc"):
            targets.append(
                ("linux-x64", "Linux x64")
            )

        if shutil.which(
            "x86_64-w64-mingw32-gcc"
        ):
            targets.append(
                ("windows-x64", "Windows x64")
            )

    elif host == "windows":
        if (
            shutil.which("gcc")
            or shutil.which("clang")
        ):
            targets.append(
                ("windows-x64", "Windows x64")
            )

    if not targets:
        raise RuntimeError(
            "No supported C compiler was found."
        )

    if len(targets) == 1:
        target_id, target_name = targets[0]

        print()
        print(
            f"Target: {target_name}"
        )

        return target_id
        # Return only available target

    print()
    print("Target platform:")

    for index, (_, target_name) in enumerate(
        targets,
        start=1
    ):
        print(
            f"({index}) {target_name}"
        )

    choice = input("> ").strip()

    try:
        selected = int(choice) - 1

        if selected < 0:
            raise IndexError

        target_id, _ = targets[selected]

    except (ValueError, IndexError):
        raise ValueError(
            "Invalid target platform"
        )

    return target_id
    # Return selected target platform


def ask_program_execution(
    target,
    host
):
    print()

    if (
        host == "linux"
        and target == "windows-x64"
    ):
        print(
            "Run the program with Wine?"
        )

    else:
        print(
            "Run the program?"
        )

    print("(y) Yes")
    print("(n) No")

    choice = input("> ").strip().lower()

    if choice not in ("y", "n"):
        raise ValueError(
            "Invalid execution choice"
        )

    return choice == "y"
    # Return program execution choice


def load_source_file():
    source_file = Path("example.vq")

    if not source_file.exists():
        raise FileNotFoundError(
            "Source file 'example.vq' was not found."
        )

    source = source_file.read_text(
        encoding="utf-8"
    )

    return source
    # Return Visual Quar source text


def build_frontend(source):
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    program = parser.parse()

    semantic = SemanticAnalyzer()

    validated_program = semantic.analyze(
        program
    )

    return validated_program
    # Return validated program AST


def run_qrvm(validated_program):
    compiler = QRVMCompiler()

    instructions = compiler.compile(
        validated_program
    )

    vm = QRVM()

    print()
    print("=== QRVM OUTPUT ===")

    vm.run(instructions)

    print()
    print(
        "Program executed successfully"
    )


def write_c_source(c_source):
    output_directory = Path("build")

    output_directory.mkdir(
        exist_ok=True
    )

    output_file = (
        output_directory / "generated.c"
    )

    output_file.write_text(
        c_source,
        encoding="utf-8"
    )

    return output_file
    # Return generated C file path


def compile_c_source(
    source_file,
    target,
    host
):
    if target == "linux-x64":
        compiler = "gcc"

        output_file = (
            source_file.parent / "program"
        )

    elif target == "windows-x64":
        output_file = (
            source_file.parent / "program.exe"
        )

        if host == "linux":
            compiler = (
                "x86_64-w64-mingw32-gcc"
            )

        elif host == "windows":
            if shutil.which("gcc"):
                compiler = "gcc"

            elif shutil.which("clang"):
                compiler = "clang"

            else:
                raise RuntimeError(
                    "Windows C compiler not found."
                )

        else:
            raise RuntimeError(
                "Windows target is not supported "
                "on this host."
            )

    else:
        raise RuntimeError(
            f"Unsupported target '{target}'"
        )

    print()
    print(
        f"Compiling {target}..."
    )

    result = subprocess.run(
        [
            compiler,
            str(source_file),
            "-o",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "C compilation failed:\n"
            f"{result.stderr}"
        )

    return output_file
    # Return compiled executable path


def run_native_executable(
    executable_file
):
    result = subprocess.run(
        [
            str(
                executable_file.resolve()
            )
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Program execution failed:\n"
            f"{result.stderr}"
        )

    return result.stdout
    # Return native program output


def run_windows_with_wine(
    executable_file
):
    result = subprocess.run(
        [
            "wine",
            str(executable_file.resolve()),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Wine execution failed:\n"
            f"{result.stderr}"
        )

    return result.stdout
    # Return Wine program output


def execute_compiled_program(
    executable_file,
    target,
    host
):
    if target == "linux-x64":
        if host != "linux":
            raise RuntimeError(
                "Linux executable cannot run "
                "natively on this host."
            )

        return run_native_executable(
            executable_file
        )

    if target == "windows-x64":
        if host == "windows":
            return run_native_executable(
                executable_file
            )

        if host == "linux":
            if not shutil.which("wine"):
                print()
                print(
                    "Wine not found. "
                    "Windows execution skipped."
                )
                return None

            return run_windows_with_wine(
                executable_file
            )

    raise RuntimeError(
        "Executable cannot run on this host."
    )


def run_compiled(
    validated_program,
    target,
    host
):
    generator = CCodeGenerator()

    c_source = generator.generate(
        validated_program
    )

    c_file = write_c_source(
        c_source
    )

    executable_file = compile_c_source(
        c_file,
        target,
        host
    )

    print()
    print(
        "Compilation completed successfully."
    )

    print(
        f"Executable: {executable_file}"
    )



    if not ask_program_execution(
        target,
        host
    ):
        return executable_file


    program_output = (
        execute_compiled_program(
            executable_file,
            target,
            host
        )
    )

    if program_output is not None:
        print()
        print("=== PROGRAM OUTPUT ===")

        print(
            program_output,
            end=""
        )

        print()
        print(
            "Program executed successfully."
        )

    return executable_file
    # Return compiled executable path


def main():
    try:
        source = load_source_file()

        mode = select_execution_mode()

        validated_program = build_frontend(
            source
        )

        if mode == "a":
            run_qrvm(
                validated_program
            )
            return

        host = detect_host()

        print()
        print(
            f"Host platform: {host}"
        )

        target = select_target_platform(
            host
        )

        run_compiled(
            validated_program,
            target,
            host
        )

    except LexerError as error:
        print(
            f"Lexer error: {error}"
        )

    except ParserError as error:
        print(
            f"Parser error: {error}"
        )

    except SemanticError as error:
        print(
            f"Semantic error: {error}"
        )

    except RuntimeError as error:
        print(
            f"Runtime error: {error}"
        )

    except ValueError as error:
        print(
            f"Configuration error: {error}"
        )

    except FileNotFoundError as error:
        print(
            f"File error: {error}"
        )


if __name__ == "__main__":
    main()