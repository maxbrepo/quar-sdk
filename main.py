import contextlib
import io
import platform
import re
import shutil
import subprocess
import sys
from unittest.mock import patch
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
from qrvm.vm import QRVM, QuarExit, QuarPanic
from feature_status import FEATURES, VIEWS
from tooling.source_projection import (
    CANONICAL_PROFILE,
    SourceLanguage,
    SourceProfile,
    VocabularyStyle,
    normalize_source,
)



def parse_c_layout_option(arguments):
    """Extract the experimental C layout option without changing other CLI flags."""
    from tooling.ir_build import CLayout

    remaining = []
    selected = CLayout.SINGLE
    iterator = iter(arguments)
    for argument in iterator:
        if argument == "--c-layout":
            try:
                selected = CLayout(next(iterator))
            except StopIteration as exc:
                raise ValueError("Missing value for --c-layout") from exc
        else:
            remaining.append(argument)
    return remaining, selected


def select_c_layout():
    """Select single-file or split C output for experimental IR builds."""
    from tooling.ir_build import CLayout

    choice = input("C layout [1] single [2] split: ").strip()
    if choice == "1":
        return CLayout.SINGLE
    if choice == "2":
        return CLayout.SPLIT
    raise ValueError("Invalid C layout selection")


def emit_ir_c_sources(source_file, layout, output_directory):
    """Lower a module project to IR and emit C artifacts via the shared builder."""
    from frontend.quar.ir import lower_program_project
    from tooling.ir_build import emit_c

    source_file = Path(source_file).resolve()
    loader = ModuleLoader(source_file.parent)
    loader.load(source_file)
    project = lower_program_project(loader, source_file)
    return emit_c(project, Path(output_directory), layout)

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
        print("[0] \\ Back")
        print("[1] cd ../")

        for index, entry in enumerate(
            entries,
            start=2,
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

        if selected == 0:
            return None

        if selected == 1:
            parent_directory = (
                current_directory.parent
            )

            if parent_directory != current_directory:
                current_directory = (
                    parent_directory.resolve()
                )

            continue

        entry_index = selected - 2

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
        print("[0] \\ Back")
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
        print("[4] External Tests")
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

        if choice == "4":
            run_external_tests()
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


def build_frontend(source, source_profile=CANONICAL_PROFILE, *, borrow_check=False, lexical=False):
    canonical_source, _ = normalize_source(
        source,
        source_profile,
    )

    # Optional strict borrow gate; default execution remains unchanged.
    if borrow_check:
        from qrvm.borrow_gate import require_borrow_source
        require_borrow_source(canonical_source)

    lexer = Lexer(canonical_source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)
    program = parser.parse()

    semantic = SemanticAnalyzer(allow_lexical_shadowing=lexical)

    validated_program = semantic.analyze(
        program
    )

    return validated_program, semantic.variables
    # Return validated AST and types


def run_qrvm(validated_program, *, lexical=False, allow_inference=False):
    compiler = QRVMCompiler()

    instructions = compiler.compile(
        validated_program, lexical=lexical, allow_inference=allow_inference
    )

    vm = QRVM()

    print()
    print("=== QRVM OUTPUT ===")

    try:
        vm.run(instructions)
    except QuarExit as error:
        print(f"Program exited with code {error.code}")
        return error.code

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
    host,
    *, lexical=False, allow_inference=False
):
    generator = CCodeGenerator()

    c_source = generator.generate(
        validated_program,
        variable_types, lexical=lexical, allow_inference=allow_inference
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
    if "input" in parts or "fixtures" in parts:
        return True
    # Module project dependencies are imported by main.vq, not standalone batch programs.
    if "13 modules" in parts:
        components = source_file.parts
        chapter_index = next((index for index, part in enumerate(components)
                              if part.lower() == "13 modules"), None)
        if (chapter_index is not None and chapter_index + 2 < len(components)
                and re.match(r"^\d+ ", components[chapter_index + 1])
                and source_file.name != "main.vq"):
            return True
    return False
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


def discover_test_features(root):
    """Return chapter/feature directory names found under version categories."""
    names = set()
    for version in list_versions(root):
        for category in list_categories(version):
            for child in category.iterdir():
                if child.is_dir() and child.name.lower() not in ("input", "fixtures"):
                    names.add(child.name)
    return sorted(names, key=lambda name: (int(re.match(r"^\d+", name).group()) if re.match(r"^\d+", name) else 999999, name.lower()))


def source_matches_feature(source_file, feature):
    """Match a feature directory exactly, never by partial filename."""
    return feature is None or feature in source_file.parts


def filter_test_sources(sources, feature):
    """Keep only sources belonging to the selected feature."""
    return [source for source in sources if source_matches_feature(source, feature)]


def select_test_feature(root, current):
    """Select a persistent feature filter; None means all features."""
    features = discover_test_features(root)
    clear_screen()
    print("Filter by feature\n")
    print(f"Current: {current or 'All features'}\n")
    print("[0] \\ Back")
    print("[1] All features (clear filter)")
    for index, feature in enumerate(features, start=2):
        print(f"[{index}] {feature}")
    choice = input("\n> ").strip()
    if not choice.isdigit() or choice == "0":
        return current
    selected = int(choice)
    if selected == 1:
        return None
    return features[selected - 2] if 2 <= selected < len(features) + 2 else current


def select_single_test_file(root, feature=None):
    current = root
    while True:
        entries = list_source_entries(current)
        if feature is not None:
            entries = [entry for entry in entries if (
                source_matches_feature(entry, feature)
                if entry.is_file() else
                entry.name == feature or any(
                    source_matches_feature(path, feature)
                    for path in entry.rglob("*.vq")
                )
            )]
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
    169: "Unknown field 'unknown'",
    170: "Constructor for 'Player' expects 1 arguments",
    181: "I/O error in File.read_text [not_found]:",
    182: "I/O error in Bytes.from_hex [invalid_data]:",
    183: "Bytes index out of bounds:",
    184: "I/O error in Directory.entry [invalid_data]:",
    189: "input prompt must be a string",
    190: "input expects zero or one string argument",
    195: "stdout argument must be a string",
    196: "exit code must be an integer",
    197: "Exit code must be between 0 and 255.",
    202: "Console.arg index out of range",
    203: "Environment variable not found: VQ_CH11C_MISSING",
    204: "Console.arg index must be an integer",
    205: "Console.env argument must be a string",
    212: "unhandled chapter 12",
    213: "throw requires a string message",
    219: "throw cause must be a caught error",
    220: "Variable 'unknown' is not declared",
    225: "Assertion failed",
    226: "assert argument must be a boolean",
    227: "assert expects one boolean argument",
    228: "fatal failure",
    229: "cannot recover",
    232: "panic message must be a string",
    233: "panic expects one string argument",

}


def regression_project_root(source_file):
    fixtures = source_file.parent / "fixtures"
    if fixtures.is_dir():
        return fixtures
    return source_file.parent
    # Return module lookup root


CONSOLE_OUTPUT_EXPECTATIONS = {
    214: ("wrapper\nroot\n", ""),
    216: ("high\nlow\n", ""),
    217: ("third\nsecond <- first\n", ""),
    218: ("standalone\n\n", ""),
    191: ("Hello World!\n", ""),
    192: ("Done\n", "Warning\n"),
    193: ("Before\n", ""),
    194: ("AB\n", ""),
    198: ("2\nfirst\nsecond\n", ""),
    199: ("ok\nTrue\nFalse\n", ""),
    200: ("0\n", ""),
    201: ("42\n", ""),
}


CONSOLE_CONTEXT_FIXTURES = {
    198: (["first", "second"], {}),
    199: ([], {"VQ_CH11C_PRESENT": "ok"}),
    200: ([], {}),
    201: (["42"], {}),
    202: ([], {}),
    203: ([], {}),
}


CONSOLE_INPUT_FIXTURES = {
    186: ["Ada"],
    187: ["42"],
    188: ["Hello"],
}


def fixture_input(values):
    iterator = iter(values)

    def read_input(prompt=""):
        print(prompt, end="")
        try:
            return next(iterator)
        except StopIteration as error:
            raise EOFError("Console fixture exhausted") from error

    return read_input


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
        error_output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error_output):
            if test_number in CONSOLE_INPUT_FIXTURES:
                with patch("builtins.input", fixture_input(CONSOLE_INPUT_FIXTURES[test_number])):
                    QRVM().run(instructions)
            else:
                args, env = CONSOLE_CONTEXT_FIXTURES.get(test_number, ([], {}))
                QRVM(args=args, environ=env).run(instructions)
    except QuarPanic as error:
        message = str(error)
        panic_detail = message.removeprefix("Panic: ")
        if expected_error is not None and panic_detail.startswith(expected_error):
            return "EXPECTED ERROR", message
        return "FAIL", f"Unexpected fatal panic: {message}"
    except QuarExit as error:
        if error.code == 0 and expected_error is None:
            expected_streams = CONSOLE_OUTPUT_EXPECTATIONS.get(test_number)
            if expected_streams is not None and (output.getvalue(), error_output.getvalue()) != expected_streams:
                return "FAIL", "Console stream output mismatch"
            return "PASS", output.getvalue().rstrip()
        return "FAIL", f"Unexpected program exit code: {error.code}"
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

    expected_streams = CONSOLE_OUTPUT_EXPECTATIONS.get(test_number)
    if expected_streams is not None and (output.getvalue(), error_output.getvalue()) != expected_streams:
        return "FAIL", "Console stream output mismatch"
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

def print_regression_results(records, root):
    """Render stored test results without executing sources again."""
    clear_screen()
    print(
        "Version | No  | Program                  | "
        "Inferred | Mixed | Typed | Result"
    )
    print("-" * 86)
    previous_version = None
    for source_file, result, output in records:
        version, _, _, _ = source_metadata(source_file, root)
        if previous_version is not None:
            print("=" * 86 if version != previous_version else "-" * 86)
        print_test_result(source_file, root, result, output)
        previous_version = version
    print("=" * 86)
    # Render a previously executed batch or a filtered subset.


def browse_regression_results(records, root):
    """Filter the most recent results without rerunning any test."""
    counts = {status: sum(result == status for _, result, _ in records)
              for status in ("PASS", "EXPECTED ERROR", "FAIL", "CRASH")}
    current = records
    while True:
        print_regression_results(current, root)
        print(
            f"Displayed: {len(current)}/{len(records)} | "
            f"PASS: {counts['PASS']} | EXPECTED ERROR: {counts['EXPECTED ERROR']} | "
            f"FAIL: {counts['FAIL']} | CRASH: {counts['CRASH']}"
        )
        print("\nSelect: [0] \\ Back, [1] All, [2] Failures, [3] Crash, [4] Pass, [5] Expected error")
        choice = input("> ").strip()
        if choice == "0":
            return
        if choice == "1":
            current = records
        elif choice == "2":
            current = [entry for entry in records if entry[1] in ("FAIL", "CRASH")]
        elif choice == "3":
            current = [entry for entry in records if entry[1] == "CRASH"]
        elif choice == "4":
            current = [entry for entry in records if entry[1] == "PASS"]
        elif choice == "5":
            current = [entry for entry in records if entry[1] == "EXPECTED ERROR"]
    # Keep test outputs available until the user exits this results screen.


def run_regression_batch(source_files, root):
    """Execute tests once, then offer post-run result filtering."""
    records = []
    for source_file in source_files:
        result, output = execute_regression_source(source_file)
        records.append((source_file, result, output))
    browse_regression_results(records, root)
    # Run classified regression batch and inspect failures without rerunning.

def test_single_file(root, feature=None):
    source_file = select_single_test_file(root, feature)
    if source_file is None:
        return
    run_regression_batch([source_file], root)
    # Test one selected source


def test_range(root, feature=None):
    version = select_numbered_item("Select version:", list_versions(root))
    if version is None:
        return
    category = select_numbered_item(f"Version {version.name}", list_categories(version))
    if category is None:
        return
    sources = filter_test_sources(collect_batch_sources(category), feature)
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


def test_category(root, feature=None):
    version = select_numbered_item("Select version:", list_versions(root))
    if version is None:
        return
    category = select_numbered_item(f"Version {version.name}", list_categories(version))
    if category is None:
        return
    run_regression_batch(filter_test_sources(collect_batch_sources(category), feature), root)
    # Test one source category


def test_version(root, feature=None):
    version = select_numbered_item("Select version:", list_versions(root))
    if version is None:
        return
    run_regression_batch(filter_test_sources(collect_batch_sources(version), feature), root)
    # Test complete version


def test_all_versions(root, feature=None):
    sources = []
    for version in list_versions(root):
        sources.extend(collect_batch_sources(version))
    run_regression_batch(filter_test_sources(sources, feature), root)
    # Test every available version


def run_source_tester():
    root = find_examples_root()
    feature = None
    while True:
        clear_screen()
        print("Visual Quar Source Tester\n")
        print(f"Root: {root}")
        print(f"Feature filter: {feature or 'All features'}\n")
        print("[0] \\ Back")
        print("[1] Test single file")
        print("[2] Test range")
        print("[3] Test version category")
        print("[4] Test version")
        print("[5] Test all versions")
        print("[6] Filter by feature")
        choice = input("\n> ").strip()
        if choice == "0":
            return
        if choice == "1":
            test_single_file(root, feature)
        elif choice == "2":
            test_range(root, feature)
        elif choice == "3":
            test_category(root, feature)
        elif choice == "4":
            test_version(root, feature)
        elif choice == "5":
            test_all_versions(root, feature)
        elif choice == "6":
            feature = select_test_feature(root, feature)
    # Run terminal source tester


def discover_external_test_files():
    tests_root = Path(__file__).resolve().parent / "tests"
    if not tests_root.is_dir():
        return tests_root, []
    files = sorted(tests_root.glob("test_*.py"))
    return tests_root, [path for path in files if path.is_file()]
    # Return the test directory and available unittest files


def run_external_test_selection(files):
    if not files:
        print("No matching external tests found.")
        input("\nPress Enter to continue...")
        return False

    project_root = Path(__file__).resolve().parent
    tests_root = project_root / "tests"
    command = [
        sys.executable, "-m", "unittest", "discover",
        "-s", str(tests_root), "-p", "test_*.py",
    ]
    # For a selection, use explicit module paths with a stable working directory.
    if len(files) != len(discover_external_test_files()[1]):
        command = [
            sys.executable, "-m", "unittest",
            *[f"tests.{path.stem}" for path in files],
        ]
    print(f"\nRunning {len(files)} external test files...\n")
    result = subprocess.run(command, cwd=project_root, check=False)
    print(f"\nExternal tests: {'PASS' if result.returncode == 0 else 'FAIL'}")
    print(f"Exit code: {result.returncode}")
    input("\nPress Enter to continue...")
    return result.returncode == 0
    # Run unittest in a child process and return its success status


def run_external_tests():
    while True:
        clear_screen()
        tests_root, files = discover_external_test_files()
        print("Visual Quar External Tests\n")
        print(f"Root: {tests_root}")
        print(f"Available files: {len(files)}\n")
        print("[0] Back")
        print("[1] Run all tests")
        print("[2] Run tests by chapter")
        print("[3] Run tests by block")
        print("[4] Run single test file")
        choice = input("\n> ").strip()
        if choice == "0":
            return
        if choice == "1":
            run_external_test_selection(files)
            continue
        if choice not in ("2", "3", "4"):
            continue
        if choice == "4":
            options = files
            label = "Select test file"
        else:
            import re as regex
            pattern = r"^test_ch(\d+)_" if choice == "2" else r"^test_ch(\d+_\d+)_"
            keys = sorted({match.group(1) for path in files if (match := regex.match(pattern, path.name))},
                          key=lambda key: tuple(int(part) for part in key.split("_")))
            options = keys
            label = "Select chapter" if choice == "2" else "Select block"
        print(f"\n{label}:")
        print("[0] Back")
        for index, option in enumerate(options, 1):
            print(f"[{index}] {option.name if isinstance(option, Path) else option}")
        selected = input("\n> ").strip()
        if not selected.isdigit() or not 1 <= int(selected) <= len(options):
            continue
        item = options[int(selected) - 1]
        if choice == "4":
            selected_files = [item]
        else:
            prefix = f"test_ch{item}_"
            selected_files = [path for path in files if path.name.startswith(prefix)]
        run_external_test_selection(selected_files)
    # Display the external unittest menu and run selected tests


def extract_inspector_flag(arguments):
    """Return (remaining arguments, enabled); reject repeated flags."""
    enabled = arguments.count("--inspect")
    if enabled > 1:
        raise ValueError("--inspect may be specified only once")
    return [argument for argument in arguments if argument != "--inspect"], bool(enabled)


def parse_lexical_options(arguments):
    """Extract explicit experimental compiler options from CLI arguments.

    Returns the remaining source arguments and two boolean feature flags.
    The inference flag is valid only when lexical lowering is enabled.
    """
    if arguments.count("--lexical") > 1:
        raise ValueError("--lexical may be specified only once")
    if arguments.count("--lexical-inference") > 1:
        raise ValueError("--lexical-inference may be specified only once")
    lexical = "--lexical" in arguments
    inference = "--lexical-inference" in arguments
    if inference and not lexical:
        raise ValueError("--lexical-inference requires --lexical")
    remaining = [
        argument for argument in arguments
        if argument not in ("--lexical", "--lexical-inference")
    ]
    return remaining, lexical, inference


def main():
    try:
        source_arguments, lexical, allow_inference = parse_lexical_options(sys.argv[1:])
        arguments, inspect_enabled = extract_inspector_flag(source_arguments)
        kart_enabled = "--kart" in arguments
        if arguments.count("--kart") > 1:
            raise ValueError("--kart may be specified only once")
        if kart_enabled and lexical:
            raise ValueError("--lexical is not yet supported with --kart")
        arguments = [argument for argument in arguments if argument != "--kart"]
        (
            source_file,
            source_profile,
        ) = parse_source_argument(arguments)

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

        if kart_enabled:
            project_root = source_file.parent
            program = ModuleLoader(project_root, kart_project=project_root).load(source_file)
            validated_program = SemanticAnalyzer().analyze(program)
            variable_types = {}
        else:
            (
                validated_program,
                variable_types,
            ) = build_frontend(
                source,
                source_profile,
                lexical=lexical,
            )

        if inspect_enabled:
            from qrvm.inspector_pipeline import (
                inspect_validated_program,
                format_pipeline_inspection,
            )
            inspection = inspect_validated_program(validated_program, path=str(source_file))
            print(format_pipeline_inspection(inspection))
            # Inspector is advisory; semantic validation remains authoritative.

        if mode == "1":
            run_qrvm(
                validated_program,
                lexical=lexical,
                allow_inference=allow_inference,
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
            host,
            lexical=lexical,
            allow_inference=allow_inference,
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