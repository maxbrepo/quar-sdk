import contextlib
import io
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from frontend.quar.lexer import Lexer
from frontend.quar.parser import Parser
from frontend.quar.semantic import SemanticAnalyzer
from frontend.quar.module_loader import ModuleLoader, ModuleLoadError

from frontend.quar.errors import (
    LexerError,
    ParserError,
    SemanticError,
)

from backend.c.codegen import CCodeGenerator

from qrvm.compiler import QRVMCompiler
from qrvm.vm import QRVM
from feature_status import FEATURES, VIEWS
from tooling.source_projection import (
    CANONICAL_PROFILE,
    SourceLanguage,
    SourceProfile,
    VocabularyStyle,
    normalize_source,
)


def clear_screen():
    command = (
        "cls"
        if platform.system().lower() == "windows"
        else "clear"
    )

    subprocess.run(
        command,
        shell=True,
        check=False,
    )
    # Clear terminal screen


def select_execution_mode():
    clear_screen()

    print("Execution mode:")
    print("[1] Interpreted")
    print("[2] Compiled")

    choice = input("> ").strip()

    if choice not in ("1", "2"):
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

    print("[1] Yes")
    print("[2] No")

    choice = input("> ").strip()

    if choice not in ("1", "2"):
        raise ValueError(
            "Invalid execution choice"
        )

    return choice == "1"
    # Return program execution choice


def validate_source_file(source_file):
    source_file = source_file.expanduser()

    if source_file.suffix.lower() != ".vq":
        raise ValueError(
            "Source file must use the '.vq' extension."
        )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Source file '{source_file}' was not found."
        )

    if not source_file.is_file():
        raise ValueError(
            f"Source path '{source_file}' is not a file."
        )

    return source_file
    # Return validated source path


def load_source_file(source_file):
    source_file = validate_source_file(
        source_file
    )

    source = source_file.read_text(
        encoding="utf-8"
    )

    return source
    # Return Visual Quar source text


def list_source_entries(directory):
    directories = sorted(
        [
            entry
            for entry in directory.iterdir()
            if entry.is_dir()
        ],
        key=lambda entry: entry.name.lower(),
    )

    source_files = sorted(
        [
            entry
            for entry in directory.iterdir()
            if (
                entry.is_file()
                and entry.suffix.lower() == ".vq"
            )
        ],
        key=lambda entry: entry.name.lower(),
    )

    return directories + source_files
    # Return browsable source entries


def browse_source_file():
    current_directory = Path.cwd().resolve()

    while True:
        clear_screen()

        entries = list_source_entries(
            current_directory
        )

        print()
        print("Load Visual Quar Source")
        print()
        print(current_directory)
        print()
        print("[1] Exit")
        print("[2] /")

        for index, entry in enumerate(
            entries,
            start=3,
        ):
            if entry.is_dir():
                print(
                    f"[{index}]/ {entry.name}/"
                )
            else:
                print(
                    f"[{index}]  {entry.name}"
                )

        print()
        choice = input("Select: > ").strip()

        try:
            selected = int(choice)
        except ValueError:
            print("Invalid selection.")
            continue

        if selected == 1:
            return None

        if selected == 2:
            parent_directory = (
                current_directory.parent
            )

            if parent_directory != current_directory:
                current_directory = (
                    parent_directory.resolve()
                )

            continue

        entry_index = selected - 3

        if (
            entry_index < 0
            or entry_index >= len(entries)
        ):
            print("Invalid selection.")
            continue

        selected_entry = entries[
            entry_index
        ]

        if selected_entry.is_dir():
            current_directory = (
                selected_entry.resolve()
            )
            continue

        return selected_entry
        # Return selected Visual Quar source



def read_navigation_key():
    if platform.system().lower() == "windows":
        import msvcrt
        key = msvcrt.getwch()
        if key == "\x1b":
            return "ESC"
        if key in ("\x00", "\xe0"):
            code = msvcrt.getwch()
            if code == "K":
                return "LEFT"
            if code == "M":
                return "RIGHT"
        return key

    import termios
    import tty
    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        key = sys.stdin.read(1)
        if key == "\x1b":
            second = sys.stdin.read(1)
            if second != "[":
                return "ESC"
            third = sys.stdin.read(1)
            if third == "D":
                return "LEFT"
            if third == "C":
                return "RIGHT"
            return "ESC"
        return key
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
    # Return normalized navigation key


def feature_page(title, features):
    page_size = 30
    page = 0
    pages = max(1, (len(features) + page_size - 1) // page_size)
    while True:
        clear_screen()
        print(f"Visual Quar - Feature Status - {title}\n")
        start = page * page_size
        visible = features[start:start + page_size]
        if not visible:
            print("No features in this category.")
        for index, feature in enumerate(visible, start=start + 1):
            print(
                f"{index:>3}. {feature.name:<30} "
                f"{feature.maturity:<12} {feature.dependency:<16} "
                f"QRVM:{feature.qrvm:<9} Native:{feature.native:<9} "
                f"Tests:{feature.validation}"
            )
        print(f"\nPage {page + 1}/{pages} | Left/Right: page | Esc: back")
        key = read_navigation_key()
        if key == "ESC":
            return
        if key == "LEFT" and page > 0:
            page -= 1
        elif key == "RIGHT" and page + 1 < pages:
            page += 1
    # Browse feature status pages


def run_feature_status():
    while True:
        clear_screen()
        print("Visual Quar - Feature Status\n")
        for index, (name, _) in enumerate(VIEWS, start=1):
            print(f"[{index}] {name}")
        print("[0] Back")
        choice = input("\n> ").strip()
        if choice == "0":
            return
        if not choice.isdigit():
            continue
        selected = int(choice) - 1
        if not 0 <= selected < len(VIEWS):
            continue
        title, predicate = VIEWS[selected]
        features = [feature for feature in FEATURES if predicate(feature)]
        feature_page(title, features)
    # Run feature status browser


def select_source_file():
    while True:
        clear_screen()

        print("Visual Quar")
        print()
        print("[0] * Exit")
        print("[1] Examples")
        print("[2] Load")
        print("[3] Features")
        print()

        choice = input("> ").strip()

        if choice == "0":
            return None

        if choice == "1":
            run_source_tester()
            continue

        if choice == "3":
            run_feature_status()
            continue

        if choice == "2":
            source_file = browse_source_file()

            if source_file is not None:
                return source_file

            continue
    # Return selected Visual Quar source


def parse_source_argument(args):
    if len(args) == 1 and args[0] == "-l":
        return select_source_file(), CANONICAL_PROFILE

    if len(args) >= 2 and args[0] == "-f":
        source_file = validate_source_file(
            Path(args[1])
        )

        language = SourceLanguage.ENGLISH
        vocabulary = VocabularyStyle.CANONICAL
        index = 2

        while index < len(args):
            option = args[index]

            if option == "--lang" and index + 1 < len(args):
                language = SourceLanguage(args[index + 1])
                index += 2
                continue

            if option == "--vocabulary" and index + 1 < len(args):
                vocabulary = VocabularyStyle(args[index + 1])
                index += 2
                continue

            raise ValueError(
                f"Unknown or incomplete source option '{option}'"
            )

        return source_file, SourceProfile(
            language=language,
            vocabulary=vocabulary,
        )

    raise ValueError(
        "Usage: quarc -f <source.vq> "
        "[--lang en|it|es] "
        "[--vocabulary canonical|extended] | quarc -l"
    )


def build_frontend(source, source_profile=CANONICAL_PROFILE):
    canonical_source, _ = normalize_source(
        source,
        source_profile,
    )

    lexer = Lexer(canonical_source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    program = parser.parse()

    semantic = SemanticAnalyzer()

    validated_program = semantic.analyze(
        program
    )

    return validated_program, semantic.variables
    # Return validated AST and types


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
    variable_types,
    target,
    host
):
    generator = CCodeGenerator()

    c_source = generator.generate(
        validated_program,
        variable_types
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



TEST_CATEGORIES = ("inferred", "mixed", "typed")


def extract_test_number(source_file):
    match = re.match(r"^(\d+)", source_file.stem)
    return int(match.group(1)) if match else None
    # Return leading test number


def extract_test_name(source_file):
    name = re.sub(r"^\d+[\s_-]*", "", source_file.stem)
    return name or source_file.stem
    # Return readable test name


def is_excluded_batch_source(source_file):
    parts = {part.lower() for part in source_file.parts}
    return "input" in parts or "fixtures" in parts
    # Detect non-batch source path


def collect_batch_sources(directory):
    sources = [
        path for path in directory.rglob("*.vq")
        if not is_excluded_batch_source(path)
    ]
    return sorted(
        sources,
        key=lambda path: (
            extract_test_number(path) if extract_test_number(path) is not None else 999999,
            str(path).lower(),
        ),
    )
    # Return non-interactive sources


def version_key(name):
    return tuple(int(part) for part in name.split("."))
    # Return sortable version tuple


def find_examples_root():
    for candidate in (Path.cwd() / "examples", Path.cwd() / "sources", Path.cwd()):
        if candidate.exists() and any(
            item.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+", item.name)
            for item in candidate.iterdir()
        ):
            return candidate.resolve()
    return Path.cwd().resolve()
    # Return source test root


def list_versions(root):
    versions = [
        item for item in root.iterdir()
        if item.is_dir() and re.fullmatch(r"\d+\.\d+\.\d+", item.name)
    ]
    return sorted(versions, key=lambda item: version_key(item.name))
    # Return available versions


def select_numbered_item(title, items):
    clear_screen()
    print(title)
    print()
    print("[0] \\ Back")
    for index, item in enumerate(items, start=1):
        print(f"[{index}] {item.name}")
    choice = input("\n> ").strip()
    if not choice.isdigit():
        return None
    selected = int(choice)
    if selected == 0:
        return None
    index = selected - 1
    return items[index] if 0 <= index < len(items) else None
    # Return selected menu item


def list_categories(version_directory):
    return [
        version_directory / name
        for name in TEST_CATEGORIES
        if (version_directory / name).is_dir()
    ]
    # Return available categories


def select_single_test_file(root):
    current = root
    while True:
        entries = list_source_entries(current)
        clear_screen()
        print("Test single file\n")
        print(current)
        print("\n[0] \\ Back")
        for index, entry in enumerate(entries, start=1):
            marker = "/" if entry.is_dir() else " "
            suffix = "/" if entry.is_dir() else ""
            print(f"[{index}]{marker} {entry.name}{suffix}")
        choice = input("\n> ").strip()
        if not choice.isdigit():
            continue
        selected = int(choice)
        if selected == 0:
            if current == root:
                return None
            current = current.parent
            continue
        index = selected - 1
        if not 0 <= index < len(entries):
            continue
        entry = entries[index]
        if entry.is_dir():
            current = entry.resolve()
            continue
        return entry
        # Return selected test file


EXPECTED_TEST_ERRORS = {
    46: "Duplicate import:",
    47: "Module not found:",
    48: "Circular module dependency:",
    51: "Overflow error:",
    52: "Underflow error:",
    56: "Cannot assign to constant",
    60: "Precision loss:",
    70: "Division by zero",
    71: "Modulo by zero",
    82: "Duplicate default",
    83: "Duplicate case value",
    93: "Incoherent for direction",
    94: "Infinite loop:",
    95: "Infinite loop:",
    105: "Function 'add' missing required argument 'right'",
    106: "Function 'add' has no parameter 'other'",
    107: "Argument 'left' is specified more than once",
    108: "Positional argument cannot follow a named argument",
    109: "Required parameter cannot follow a default parameter",
    110: "Default value for parameter 'multiplier' expects 'i32', received 'string'",
    115: "Array index out of bounds:",
    116: "Array index out of bounds:",
    123: "Array index out of bounds:",
    124: "Array index out of bounds:",
    131: "Substring range out of bounds.",
    138: "String conversion failed in 'to_int'.",
    145: "Record 'Point' is immutable",
    150: "Destructuring arity mismatch",
    154: "Non-exhaustive match; missing:",
    155: "Invalid payload for variant 'SUCCESS'",
    156: "Duplicate match variant 'SUCCESS'",
    160: "Variant 'SUCCESS' expects 1 bindings",
}


def regression_project_root(source_file):
    fixtures = source_file.parent / "fixtures"
    if fixtures.is_dir():
        return fixtures
    return source_file.parent
    # Return module lookup root


def execute_regression_source(source_file):
    test_number = extract_test_number(source_file)
    expected_error = EXPECTED_TEST_ERRORS.get(test_number)

    try:
        program = ModuleLoader(
            regression_project_root(source_file)
        ).load(source_file)
        validated_program = SemanticAnalyzer().analyze(program)
        instructions = QRVMCompiler().compile(validated_program)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            QRVM().run(instructions)
    except (
        ModuleLoadError,
        LexerError,
        ParserError,
        SemanticError,
        RuntimeError,
        ValueError,
        FileNotFoundError,
    ) as error:
        message = str(error)
        if expected_error is not None:
            if message.startswith(expected_error):
                return "EXPECTED ERROR", message
            return (
                "FAIL",
                "Expected error does not match.\n"
                f"Expected: {expected_error}\n"
                f"Received: {message}"
            )
        return "FAIL", message
    except Exception as error:
        return "CRASH", f"{type(error).__name__}: {error}"

    if expected_error is not None:
        return "FAIL", f"Expected error was not raised: {expected_error}"

    return "PASS", output.getvalue().rstrip()
    # Return classified test result

def source_metadata(source_file, root):
    parts = source_file.relative_to(root).parts
    version = next((p for p in parts if re.fullmatch(r"\d+\.\d+\.\d+", p)), "-")
    category = next((p for p in parts if p in TEST_CATEGORIES), "-")
    number = extract_test_number(source_file)
    return version, (f"{number:03d}" if number is not None else "---"), extract_test_name(source_file), category
    # Return test display metadata


def print_test_result(source_file, root, result, output):
    version, number, program, category = source_metadata(source_file, root)
    flags = {name: "-" for name in TEST_CATEGORIES}
    if category in flags:
        flags[category] = "V"
    print(
        f"{version:<7} | {number:<3} | {program:<24} | "
        f"{flags['inferred']:^8} | {flags['mixed']:^5} | "
        f"{flags['typed']:^5} | {result}"
    )
    if output:
        print(output)
    # Print one classified result

def run_regression_batch(source_files, root):
    clear_screen()
    print(
        "Version | No  | Program                  | "
        "Inferred | Mixed | Typed | Result"
    )
    print("-" * 86)
    counts = {
        "PASS": 0,
        "EXPECTED ERROR": 0,
        "FAIL": 0,
        "CRASH": 0,
    }
    previous_version = None
    for source_file in source_files:
        version, _, _, _ = source_metadata(source_file, root)
        if previous_version is not None:
            print("=" * 86 if version != previous_version else "-" * 86)
        result, output = execute_regression_source(source_file)
        print_test_result(source_file, root, result, output)
        counts[result] += 1
        previous_version = version
    print("=" * 86)
    print(
        f"Tests: {len(source_files)} | "
        f"PASS: {counts['PASS']} | "
        f"EXPECTED ERROR: {counts['EXPECTED ERROR']} | "
        f"FAIL: {counts['FAIL']} | "
        f"CRASH: {counts['CRASH']}"
    )
    input("\nPress Enter to continue...")
    # Run classified regression batch

def test_single_file(root):
    source_file = select_single_test_file(root)
    if source_file is None:
        return
    run_regression_batch([source_file], root)
    # Test one selected source


def test_range(root):
    version = select_numbered_item("Select version:", list_versions(root))
    if version is None:
        return
    category = select_numbered_item(f"Version {version.name}", list_categories(version))
    if category is None:
        return
    sources = collect_batch_sources(category)
    clear_screen()
    print(f"Available tests: {version.name}/{category.name}\n")
    for source_file in sources:
        number = extract_test_number(source_file)
        print(f"{number:03d} {source_file.name}" if number is not None else f"--- {source_file.name}")
    start_text = input("\nFrom: ").strip()
    end_text = input("To: ").strip()
    if not (start_text.isdigit() and end_text.isdigit()):
        return
    start, end = int(start_text), int(end_text)
    selected = [
        path for path in sources
        if extract_test_number(path) is not None
        and start <= extract_test_number(path) <= end
    ]
    run_regression_batch(selected, root)
    # Test numbered source range


def test_category(root):
    version = select_numbered_item("Select version:", list_versions(root))
    if version is None:
        return
    category = select_numbered_item(f"Version {version.name}", list_categories(version))
    if category is None:
        return
    run_regression_batch(collect_batch_sources(category), root)
    # Test one source category


def test_version(root):
    version = select_numbered_item("Select version:", list_versions(root))
    if version is None:
        return
    run_regression_batch(collect_batch_sources(version), root)
    # Test complete version


def test_all_versions(root):
    sources = []
    for version in list_versions(root):
        sources.extend(collect_batch_sources(version))
    run_regression_batch(sources, root)
    # Test every available version


def run_source_tester():
    root = find_examples_root()
    while True:
        clear_screen()
        print("Visual Quar Source Tester\n")
        print(f"Root: {root}\n")
        print("[0] \\ Back")
        print("[1] Test single file")
        print("[2] Test range")
        print("[3] Test category")
        print("[4] Test version")
        print("[5] Test all versions")
        choice = input("\n> ").strip()
        if choice == "0":
            return
        if choice == "1":
            test_single_file(root)
        elif choice == "2":
            test_range(root)
        elif choice == "3":
            test_category(root)
        elif choice == "4":
            test_version(root)
        elif choice == "5":
            test_all_versions(root)
    # Run terminal source tester


def main():
    try:
        (
            source_file,
            source_profile,
        ) = parse_source_argument(
            sys.argv[1:]
        )

        if source_file is None:
            print("Source loader closed.")
            return

        source = load_source_file(
            source_file
        )

        print()
        print(
            f"Source: {source_file}"
        )

        mode = select_execution_mode()

        (
            validated_program,
            variable_types,
        ) = build_frontend(
            source,
            source_profile,
        )

        if mode == "1":
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
            variable_types,
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