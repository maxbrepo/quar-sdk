import sys
import os
from pathlib import Path
import shutil

from typing import Any

from .instructions import OpCode
from .io_errors import QuarIOError, classify_io_error
from .atomic_io import write_bytes_atomic, write_text_atomic
from .call_frames import CallFrame, describe_frames
from .heap import BootstrapHeap
from .array_access import resolve_index, validate_shape
from .string_ops import string_length, string_operation
from .struct_access import create_struct, validate_fields, load_field, store_field, resolve_field
from .error_reporting import QVMDiagnostic, make_diagnostic
from .debug_hooks import DebugHook, make_event
from .profiling import InstructionProfiler, ProfileSnapshot


Instruction = tuple[OpCode, Any | None]


class _ScopedReturn:
    def __init__(self, value):
        self.value = value


class QuarExit(Exception):
    def __init__(self, code: int):
        self.code = code
        super().__init__(f"Program exited with code {code}")


class QuarPanic(BaseException):
    """Fatal program termination; ordinary try/catch cannot intercept it."""


class QuarThrownError(RuntimeError):
    def __init__(self, message: str, cause_message: str = ""):
        super().__init__(message)
        self.cause_message = cause_message


from dataclasses import dataclass


class QuarOptionalError(RuntimeError):
    """Raised when attempting to unwrap an absent optional value."""


@dataclass(frozen=True)
class QuarOptional:
    present: bool
    value: Any = None


class QRVM:
    def __init__(self, args=None, environ=None) -> None:
        # CLI arguments exclude the executable/source path.
        self.console_args = list(args) if args is not None else []
        self.console_environ = dict(environ) if environ is not None else dict(os.environ)
        self.stack: list[int | float | bool] = []
        self.variables: dict[str, object] = {}
        self.functions: dict[str, dict] = {}
        self.class_methods: dict[tuple[str, str], dict] = {}
        self.heap = BootstrapHeap()
        self.call_frames: list[CallFrame] = []
        self.last_error_frames: tuple[str, ...] = ()
        self.last_diagnostic: QVMDiagnostic | None = None
        self.debug_hook: DebugHook | None = None
        self.profiler: InstructionProfiler | None = None

    def set_profiling(self, enabled: bool) -> None:
        """Enable or disable instruction profiling (reset on enable)."""
        if type(enabled) is not bool:
            raise TypeError("Profiling enabled flag must be bool.")
        self.profiler = InstructionProfiler() if enabled else None

    def profile_snapshot(self) -> ProfileSnapshot | None:
        """Return a detached snapshot, or None if profiling is disabled."""
        return self.profiler.snapshot() if self.profiler is not None else None

    def set_debug_hook(self, hook: DebugHook | None) -> None:
        """Install an optional observer; None disables observation."""
        if hook is not None and not callable(hook):
            raise TypeError("Debug hook must be callable or None.")
        self.debug_hook = hook

    def _emit_debug(self, phase, index, opcode, error=None) -> None:
        """Emit immutable metadata without exposing stack or locals."""
        hook = self.debug_hook
        if hook is not None:
            hook(make_event(phase, index, opcode, self.call_frames,
                            len(self.stack), error))

    def run(self, program) -> None:
        self.stack.clear()
        self.heap.reset()
        self.variables.clear()
        self.call_frames.clear()
        self.last_error_frames = ()
        self.last_diagnostic = None
        if self.profiler is not None:
            self.profiler.reset()

        if isinstance(program, dict):
            instructions = program["instructions"]
            self.functions = program["functions"]
            self.class_methods = program.get("class_methods", {})
        else:
            instructions = program
            self.functions = {}
            self.class_methods = {}

        self.execute(instructions, self.variables, frame_name="<main>")
        # Execute complete QRVM program

    def execute(
        self,
        program: list[Instruction],
        variables: dict[str, object],
        scoped: bool = False,
        *,
        frame_name: str | None = None,
        isolate_stack: bool = False,
    ):
        """Run a context and restore frame bookkeeping even on exceptions.

        Existing operand-stack behavior is intentionally unchanged.
        """
        if frame_name is None:
            frame_name = "<scope>" if scoped else "<execute>"
        frame = CallFrame(frame_name, variables, len(self.stack), scoped)
        self.call_frames.append(frame)
        try:
            result = self._execute_body(program, variables, scoped)
            if isolate_stack:
                del self.stack[frame.stack_base:]
            return result
        except Exception:
            if len(self.call_frames) > len(self.last_error_frames):
                self.last_error_frames = describe_frames(self.call_frames)
            raise
        finally:
            if isolate_stack:
                del self.stack[frame.stack_base:]
            popped = self.call_frames.pop()
            assert popped is frame

    def _execute_body(
        self,
        program: list[Instruction],
        variables: dict[str, object],
        scoped: bool = False,
    ):
        ip = 0

        while ip < len(program):
            opcode, operand = program[ip]
            ip += 1

            # Hook failures propagate as host errors, outside VM diagnostics.
            self._emit_debug("before", ip - 1, opcode)

            profiler = self.profiler
            started_ns = profiler.start() if profiler is not None else None
            function_name = self.call_frames[-1].name if self.call_frames else "<unknown>"
            try:
                if opcode == OpCode.PUSH_INT:
                    if not isinstance(operand, int):
                        raise RuntimeError(
                            "PUSH_INT requires an integer operand."
                        )
                    self.stack.append(operand)

                elif opcode == OpCode.PUSH_CHAR:
                    if not isinstance(operand, str) or len(operand) > 1:
                        raise RuntimeError(
                            "PUSH_CHAR requires zero or one character."
                        )
                    self.stack.append(operand)

                elif opcode == OpCode.PUSH_STRING:
                    if not isinstance(operand, str):
                        raise RuntimeError(
                            "PUSH_STRING requires a string."
                        )
                    self.stack.append(operand)

                elif opcode == OpCode.PUSH_DOUBLE:
                    if not isinstance(operand, float):
                        raise RuntimeError(
                            "PUSH_DOUBLE requires a double operand."
                        )
                    self.stack.append(operand)

                elif opcode == OpCode.PUSH_BOOL:
                    if not isinstance(operand, bool):
                        raise RuntimeError(
                            "PUSH_BOOL requires a boolean operand."
                        )
                    self.stack.append(operand)

                elif opcode == OpCode.LOAD:
                    if not isinstance(operand, str):
                        raise RuntimeError(
                            "LOAD requires a variable name."
                        )
                    if operand not in variables:
                        raise RuntimeError(
                            f"Unknown variable '{operand}'."
                        )
                    self.stack.append(
                        variables[operand]
                    )

                elif opcode == OpCode.STORE:
                    if not isinstance(operand, str):
                        raise RuntimeError(
                            "STORE requires a variable name."
                        )
                    if not self.stack:
                        raise RuntimeError(
                            "STORE requires a stack value."
                        )
                    variables[operand] = self.stack.pop()

                elif opcode == OpCode.OPTIONAL_SOME:
                    if not self.stack:
                        raise RuntimeError("OPTIONAL_SOME requires a stack value.")
                    self.stack.append(QuarOptional(True, self.stack.pop()))

                elif opcode == OpCode.OPTIONAL_NONE:
                    self.stack.append(QuarOptional(False))

                elif opcode == OpCode.OPTIONAL_IS_PRESENT:
                    if not self.stack:
                        raise RuntimeError("OPTIONAL_IS_PRESENT requires a stack value.")
                    value = self.stack.pop()
                    if not isinstance(value, QuarOptional):
                        raise QuarOptionalError("Presence check requires an optional value.")
                    self.stack.append(value.present)

                elif opcode == OpCode.OPTIONAL_UNWRAP:
                    if not self.stack:
                        raise RuntimeError("OPTIONAL_UNWRAP requires a stack value.")
                    value = self.stack.pop()
                    if not isinstance(value, QuarOptional):
                        raise QuarOptionalError("Unwrap requires an optional value.")
                    if not value.present:
                        raise QuarOptionalError("Cannot unwrap an absent optional value.")
                    self.stack.append(value.value)

                elif opcode == OpCode.ARRAY_NEW:
                    if not isinstance(operand, tuple):
                        raise RuntimeError(
                            "ARRAY_NEW requires array metadata."
                        )
                    if len(operand) == 5:
                        name, size, default, initial_count, second_size = operand
                        dynamic = False
                    elif len(operand) == 6:
                        name, size, default, initial_count, second_size, dynamic = operand
                    else:
                        raise RuntimeError(
                            "ARRAY_NEW received invalid metadata."
                        )
                    validate_shape(size, second_size)
                    if initial_count:
                        values = [
                            self.stack.pop()
                            for _ in range(initial_count)
                        ][::-1]
                    else:
                        values = [
                            default for _ in range(size)
                        ]
                    array_object = {
                        "__array__": values,
                        "__second_size__": second_size,
                        "__dynamic__": dynamic,
                    }
                    self.heap.register("array", array_object)
                    variables[name] = array_object

                elif opcode == OpCode.ARRAY_LOAD:
                    name, has_second = operand
                    if name not in variables:
                        raise RuntimeError(
                            f"Unknown sequence '{name}'."
                        )
                    value = variables[name]

                    if isinstance(value, bytes):
                        if has_second:
                            raise RuntimeError("Bytes accepts one index.")
                        index = self.stack.pop()
                        if type(index) is not int:
                            raise RuntimeError("Bytes index must be int.")
                        if index < 0 or index >= len(value):
                            raise RuntimeError(f"Bytes index out of bounds: {index}.")
                        self.stack.append(value[index])
                        continue

                    if isinstance(value, str):
                        if has_second:
                            raise RuntimeError(
                                "String accepts one index."
                            )
                        index = self.stack.pop()
                        if type(index) is not int:
                            raise RuntimeError("String index must be int.")
                        if index < 0 or index >= len(value):
                            raise RuntimeError(
                                f"String index out of bounds: {index}."
                            )
                        self.stack.append(value[index])
                        continue

                    if not isinstance(value, dict) or "__array__" not in value:
                        raise RuntimeError(
                            f"'{name}' is not an array."
                        )
                    array = value["__array__"]

                    if has_second:
                        second = self.stack.pop()
                        first = self.stack.pop()
                        index = resolve_index(value, first, second, two_dimensional=True)
                    else:
                        index = resolve_index(value, self.stack.pop())
                    self.stack.append(array[index])

                elif opcode == OpCode.ARRAY_STORE:
                    name, has_second = operand
                    if name not in variables:
                        raise RuntimeError(
                            f"Unknown array '{name}'."
                        )
                    value = variables[name]
                    if not isinstance(value, dict) or "__array__" not in value:
                        raise RuntimeError(
                            f"'{name}' is not an array."
                        )
                    array = value["__array__"]
                    stored = self.stack.pop()

                    if has_second:
                        second = self.stack.pop()
                        first = self.stack.pop()
                        index = resolve_index(value, first, second, two_dimensional=True)
                    else:
                        index = resolve_index(value, self.stack.pop())
                    array[index] = stored

                elif opcode == OpCode.LENGTH:
                    if operand not in variables:
                        raise RuntimeError(
                            f"Unknown value '{operand}'."
                        )
                    value = variables[operand]
                    if isinstance(value, str):
                        self.stack.append(string_length(value))
                    elif isinstance(value, dict) and "__array__" in value:
                        self.stack.append(len(value["__array__"]))
                    else:
                        raise RuntimeError(
                            "Length requires array or string."
                        )

                elif opcode == OpCode.ASSERT:
                    condition = self.stack.pop()
                    if type(condition) is not bool:
                        raise RuntimeError("assert argument must be a boolean")
                    if not condition:
                        raise RuntimeError("Assertion failed")

                elif opcode == OpCode.PANIC:
                    message = self.stack.pop()
                    if not isinstance(message, str):
                        raise RuntimeError("panic message must be a string")
                    raise QuarPanic(f"Panic: {message}")

                elif opcode == OpCode.THROW:
                    cause_message = ""
                    if operand:
                        cause = self.stack.pop()
                        if not isinstance(cause, dict) or cause.get("__type__") != "QuarError":
                            raise RuntimeError("throw cause must be a caught error")
                        fields = cause["__fields__"]
                        cause_message = fields["message"]
                        if fields.get("cause"):
                            cause_message += " <- " + fields["cause"]
                    message = self.stack.pop()
                    if not isinstance(message, str):
                        raise RuntimeError("throw requires a string message")
                    raise QuarThrownError(message, cause_message)

                elif opcode == OpCode.TRY_CATCH:
                    try_body, error_name, catch_body = operand
                    stack_base = len(self.stack)
                    self.last_error_frames = ()
                    try:
                        result = self.execute(try_body, variables, scoped=True)
                    except (RuntimeError, QuarIOError, OSError, ValueError, TypeError, ZeroDivisionError) as error:
                        del self.stack[stack_base:]
                        if error_name in variables:
                            raise RuntimeError("catch variable already exists")
                        variables[error_name] = {
                            "__type__": "QuarError",
                            "__fields__": {"message": str(error), "cause": getattr(error, "cause_message", ""),
                                           "trace": " -> ".join(self.last_error_frames)},
                        }
                        try:
                            result = self.execute(catch_body, variables, scoped=True)
                        finally:
                            del variables[error_name]
                    if isinstance(result, _ScopedReturn):
                        return result if scoped else result.value

                elif opcode == OpCode.WITH_FILE:
                    name, body = operand
                    mode = self.stack.pop()
                    path = self.stack.pop()
                    if mode not in ("r", "w", "a", "r+", "w+", "a+", "rb", "wb", "ab"):
                        raise RuntimeError("Unsupported file open mode")
                    if name in variables:
                        raise RuntimeError("File handle already exists")
                    try:
                        with open(path, mode, encoding=None if "b" in mode else "utf-8") as stream:
                            variables[name] = stream
                            try:
                                result = self.execute(body, variables, scoped=True)
                            finally:
                                del variables[name]
                    except OSError as error:
                        raise QuarIOError("File.open", classify_io_error(error), str(error)) from error
                    if isinstance(result, _ScopedReturn):
                        return result if scoped else result.value

                elif opcode == OpCode.HANDLE_OP:
                    name, method, count = operand
                    stream = variables.get(name)
                    if stream is None or stream.closed:
                        raise RuntimeError("File handle is not open")
                    args = [self.stack.pop() for _ in range(count)][::-1]
                    try:
                        if method == "read_all":
                            self.stack.append(stream.read())
                        elif method == "read_line":
                            self.stack.append(stream.readline())
                        elif method == "write":
                            stream.write(args[0])
                        elif method == "seek":
                            stream.seek(args[0])
                        else:
                            raise RuntimeError("Unknown file method")
                    except (OSError, UnicodeError, ValueError) as error:
                        raise QuarIOError(
                            f"File.{method}", classify_io_error(error), str(error)
                        ) from error

                elif opcode == OpCode.FILE_OP:
                    name, argument_count = operand
                    arguments = [self.stack.pop() for _ in range(argument_count)][::-1]
                    path = Path(arguments[0]) if not name.startswith("Bytes.") else None
                    try:
                        if name == "Bytes.from_hex":
                            result = bytes.fromhex(arguments[0])
                        elif name == "Bytes.to_hex":
                            result = arguments[0].hex()
                        elif name == "Bytes.length":
                            result = len(arguments[0])
                        elif name == "File.read_bytes":
                            result = path.read_bytes()
                        elif name == "File.write_bytes_atomic":
                            write_bytes_atomic(path, arguments[1])
                            result = None
                        elif name == "File.write_bytes":
                            path.write_bytes(arguments[1])
                            result = None
                        elif name == "File.append_bytes":
                            with path.open("ab") as stream:
                                stream.write(arguments[1])
                            result = None
                        elif name == "File.read_bytes_range":
                            offset, length = arguments[1:]
                            if type(offset) is not int or type(length) is not int or offset < 0 or length < 0:
                                raise ValueError("Offset and length must be nonnegative integers")
                            with path.open("rb") as stream:
                                stream.seek(offset)
                                result = stream.read(length)
                        elif name == "File.read_text":
                            result = path.read_text(encoding="utf-8")
                        elif name == "File.write_text_atomic":
                            write_text_atomic(path, arguments[1])
                            result = None
                        elif name == "File.write_text":
                            path.write_text(arguments[1], encoding="utf-8")
                            result = None
                        elif name == "File.append_text":
                            with path.open("a", encoding="utf-8") as stream:
                                stream.write(arguments[1])
                            result = None
                        elif name == "File.exists":
                            result = path.is_file()
                        elif name == "File.delete":
                            path.unlink()
                            result = None
                        elif name == "File.copy":
                            shutil.copyfile(path, Path(arguments[1]))
                            result = None
                        elif name == "File.move":
                            shutil.move(str(path), str(Path(arguments[1])))
                            result = None
                        elif name == "Directory.create":
                            path.mkdir()
                            result = None
                        elif name == "Directory.exists":
                            result = path.is_dir()
                        elif name == "Directory.delete":
                            path.rmdir()
                            result = None
                        elif name == "Path.join":
                            result = str(path / arguments[1])
                        elif name == "Path.name":
                            result = path.name
                        elif name == "Path.parent":
                            result = str(path.parent)
                        elif name == "File.read_line":
                            index = arguments[1]
                            if type(index) is not int or index < 0:
                                raise RuntimeError("Line index must be a nonnegative integer")
                            with path.open("r", encoding="utf-8") as stream:
                                for line_number, line in enumerate(stream):
                                    if line_number == index:
                                        result = line.removesuffix("\n").removesuffix("\r")
                                        break
                                else:
                                    raise RuntimeError("Line index out of range")
                        elif name == "File.read_range":
                            offset, length = arguments[1:]
                            if type(offset) is not int or type(length) is not int or offset < 0 or length < 0:
                                raise RuntimeError("Offset and length must be nonnegative integers")
                            with path.open("r", encoding="utf-8") as stream:
                                stream.seek(offset)
                                result = stream.read(length)
                        elif name == "File.size":
                            if not path.is_file():
                                raise IsADirectoryError(f"Not a regular file: {path}")
                            result = path.stat().st_size
                        elif name == "Directory.count":
                            result = sum(1 for _ in path.iterdir())
                        elif name == "Directory.create_all":
                            path.mkdir(parents=True, exist_ok=True)
                            result = None
                        elif name == "File.line_count":
                            with path.open("r", encoding="utf-8") as stream:
                                result = sum(1 for _ in stream)
                        elif name == "File.read_bytes_hex":
                            result = path.read_bytes().hex()
                        elif name == "File.write_bytes_hex":
                            path.write_bytes(bytes.fromhex(arguments[1]))
                            result = None
                        elif name == "File.append_bytes_hex":
                            with path.open("ab") as stream:
                                stream.write(bytes.fromhex(arguments[1]))
                            result = None
                        elif name == "File.read_bytes_hex_range":
                            offset, length = arguments[1:]
                            if type(offset) is not int or type(length) is not int or offset < 0 or length < 0:
                                raise RuntimeError("Offset and length must be nonnegative integers")
                            with path.open("rb") as stream:
                                stream.seek(offset)
                                result = stream.read(length).hex()
                        elif name == "Directory.is_empty":
                            if not path.is_dir():
                                raise NotADirectoryError(str(path))
                            result = not any(path.iterdir())
                        elif name == "Directory.list_text":
                            if not path.is_dir():
                                raise NotADirectoryError(str(path))
                            names = sorted(entry.name for entry in path.iterdir())
                            if any("\n" in entry for entry in names):
                                raise RuntimeError("Directory entry contains newline; use structured enumeration")
                            result = "\n".join(names)
                        elif name in {"Directory.entry", "Directory.entry_is_file", "Directory.entry_is_directory"}:
                            index = arguments[1]
                            if type(index) is not int or index < 0:
                                raise ValueError("Directory index must be a nonnegative integer")
                            if not path.is_dir():
                                raise NotADirectoryError(str(path))
                            entries = sorted(path.iterdir(), key=lambda entry: entry.name)
                            if index >= len(entries):
                                raise ValueError("Directory index out of range")
                            entry = entries[index]
                            if name == "Directory.entry":
                                result = entry.name
                            elif name == "Directory.entry_is_file":
                                result = entry.is_file()
                            else:
                                result = entry.is_dir()
                        elif name == "Path.suffix":
                            result = path.suffix
                        elif name == "Path.stem":
                            result = path.stem
                        elif name == "Path.absolute":
                            result = str(path.absolute())
                        elif name == "Path.normalize":
                            result = str(Path(__import__("os").path.normpath(str(path))))
                        else:
                            raise RuntimeError(f"Unknown file operation '{name}'")
                    except (OSError, UnicodeError, ValueError) as error:
                        raise QuarIOError(name, classify_io_error(error), str(error)) from error
                    self.stack.append(result)

                elif opcode == OpCode.STRING_OP:
                    name, argument_count = operand
                    if len(self.stack) < argument_count:
                        raise RuntimeError(f"String operation '{name}' has insufficient arguments.")
                    arguments = [self.stack.pop() for _ in range(argument_count)][::-1]
                    result = string_operation(name, arguments)
                    self.stack.append(result)

                elif opcode == OpCode.OBJECT_NEW:
                    is_class = len(operand) >= 4 and operand[3]
                    name, type_name, field_names = operand[:3]
                    names = validate_fields(type_name, field_names)
                    if is_class:
                        instance = create_struct(type_name, names, (0,) * len(names))
                        self.heap.register("object", instance)
                        variables[name] = instance
                        if len(operand) >= 6 and operand[4] is not None:
                            constructor, argument_count = operand[4], operand[5]
                            arguments = [self.stack.pop() for _ in range(argument_count)][::-1]
                            local_variables = dict(zip(constructor["parameters"], arguments))
                            local_variables["this"] = instance
                            self.execute(constructor["instructions"], local_variables)
                        continue
                    if len(self.stack) < len(names):
                        raise RuntimeError("OBJECT_NEW has insufficient values.")
                    values = [self.stack.pop() for _ in range(len(names))][::-1]
                    instance = create_struct(type_name, names, values)
                    self.heap.register("object", instance)
                    variables[name] = instance

                elif opcode == OpCode.MEMBER_LOAD:
                    object_name, member_name = operand
                    self.stack.append(load_field(variables, object_name, member_name))

                elif opcode == OpCode.MEMBER_STORE:
                    object_name, member_name = operand
                    if not self.stack:
                        raise RuntimeError("MEMBER_STORE requires a value.")
                    # Validate before consuming the operand stack value.
                    resolve_field(variables, object_name, member_name)
                    store_field(variables, object_name, member_name, self.stack.pop())

                elif opcode == OpCode.TUPLE_NEW:
                    count = operand
                    values = [self.stack.pop() for _ in range(count)][::-1]
                    self.stack.append(tuple(values))

                elif opcode == OpCode.TUPLE_UNPACK:
                    value = self.stack.pop()
                    if not isinstance(value, tuple) or len(value) != len(operand):
                        raise RuntimeError("Tuple destructuring failed.")
                    for name, item in zip(operand, value): variables[name] = item

                elif opcode == OpCode.VARIANT_NEW:
                    enum_name, variant_name, count = operand
                    values = [self.stack.pop() for _ in range(count)][::-1]
                    self.stack.append({"__enum__": enum_name, "__variant__": variant_name, "__payload__": values})

                elif opcode == OpCode.MATCH_VARIANT:
                    variant_name, bindings, fail_target = operand
                    value = self.stack.pop()
                    if isinstance(value, str) and "." in value:
                        current_variant = value.rsplit(".", 1)[1]
                        payload = []
                    elif isinstance(value, dict):
                        current_variant = value.get("__variant__")
                        payload = value.get("__payload__", [])
                    else:
                        current_variant = None
                        payload = []
                    if current_variant != variant_name:
                        ip = fail_target
                        continue
                    for name, item in zip(bindings, payload): variables[name] = item

                elif opcode == OpCode.POP:
                    if not self.stack:
                        raise RuntimeError(
                            "POP requires a stack value."
                        )
                    self.stack.pop()

                elif opcode == OpCode.ADD:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left + right)

                elif opcode == OpCode.SUB:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left - right)

                elif opcode == OpCode.MUL:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left * right)

                elif opcode == OpCode.DIV:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    if right == 0:
                        raise RuntimeError("Division by zero")
                    if (
                        isinstance(left, int)
                        and not isinstance(left, bool)
                        and isinstance(right, int)
                        and not isinstance(right, bool)
                    ):
                        self.stack.append(int(left / right))
                    else:
                        self.stack.append(left / right)

                elif opcode == OpCode.MOD:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    if right == 0:
                        raise RuntimeError("Modulo by zero")
                    self.stack.append(left % right)

                elif opcode == OpCode.BIT_AND:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left & right)

                elif opcode == OpCode.BIT_OR:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left | right)

                elif opcode == OpCode.BIT_XOR:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left ^ right)

                elif opcode == OpCode.SHIFT_LEFT:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    if right < 0:
                        raise RuntimeError("Negative shift count")
                    self.stack.append(left << right)

                elif opcode == OpCode.SHIFT_RIGHT:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    if right < 0:
                        raise RuntimeError("Negative shift count")
                    self.stack.append(left >> right)

                elif opcode == OpCode.BIT_NOT:
                    value = self.stack.pop()
                    self.stack.append(~value)

                elif opcode == OpCode.EQUAL:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left == right)

                elif opcode == OpCode.NOT_EQUAL:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left != right)

                elif opcode == OpCode.LESS:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left < right)

                elif opcode == OpCode.LESS_EQUAL:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left <= right)

                elif opcode == OpCode.GREATER:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left > right)

                elif opcode == OpCode.GREATER_EQUAL:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    self.stack.append(left >= right)

                elif opcode == OpCode.LOGICAL_AND:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    if not isinstance(left, bool) or not isinstance(right, bool):
                        raise RuntimeError(
                            "LOGICAL_AND requires boolean operands."
                        )
                    self.stack.append(left and right)

                elif opcode == OpCode.LOGICAL_OR:
                    right = self.stack.pop()
                    left = self.stack.pop()
                    if not isinstance(left, bool) or not isinstance(right, bool):
                        raise RuntimeError(
                            "LOGICAL_OR requires boolean operands."
                        )
                    self.stack.append(left or right)

                elif opcode == OpCode.LOGICAL_NOT:
                    value = self.stack.pop()
                    if not isinstance(value, bool):
                        raise RuntimeError(
                            "LOGICAL_NOT requires a boolean operand."
                        )
                    self.stack.append(not value)

                elif opcode == OpCode.NEGATE:
                    value = self.stack.pop()
                    if isinstance(value, bool) or not isinstance(value, (int, float)):
                        raise RuntimeError(
                            "NEGATE requires a numeric operand."
                        )
                    self.stack.append(-value)

                elif opcode == OpCode.JUMP_IF_FALSE:
                    condition = self.stack.pop()
                    if not isinstance(condition, (bool, int, float, str)):
                        raise RuntimeError(
                            "JUMP_IF_FALSE requires a truthy value."
                        )
                    if not bool(condition):
                        ip = operand
                        continue

                elif opcode == OpCode.JUMP:
                    ip = operand
                    continue

                elif opcode == OpCode.PRINT:
                    if not self.stack:
                        raise RuntimeError(
                            "PRINT requires a stack value."
                        )
                    print(self.stack.pop())

                elif opcode == OpCode.CONSOLE_WRITE:
                    value = self.stack.pop()
                    if not isinstance(value, str):
                        raise RuntimeError("Console output requires a string.")
                    stream = sys.stderr if operand == "stderr" else sys.stdout
                    print(value, end="", file=stream)

                elif opcode == OpCode.CONSOLE_QUERY:
                    if operand == "Console.arg_count":
                        self.stack.append(len(self.console_args))
                    elif operand == "Console.arg":
                        index = self.stack.pop()
                        if isinstance(index, bool) or not isinstance(index, int):
                            raise RuntimeError("Console.arg index must be an integer")
                        if index < 0 or index >= len(self.console_args):
                            raise RuntimeError("Console.arg index out of range")
                        self.stack.append(self.console_args[index])
                    elif operand in {"Console.env", "Console.env_exists"}:
                        name = self.stack.pop()
                        if not isinstance(name, str):
                            raise RuntimeError("Console environment variable name must be a string")
                        if operand == "Console.env_exists":
                            self.stack.append(name in self.console_environ)
                        elif name not in self.console_environ:
                            raise RuntimeError(f"Environment variable not found: {name}")
                        else:
                            self.stack.append(self.console_environ[name])
                    else:
                        raise RuntimeError(f"Unknown console operation: {operand}")

                elif opcode == OpCode.EXIT:
                    code = self.stack.pop()
                    if isinstance(code, bool) or not isinstance(code, int):
                        raise RuntimeError("Exit code must be an integer.")
                    if code < 0 or code > 255:
                        raise RuntimeError("Exit code must be between 0 and 255.")
                    raise QuarExit(code)

                elif opcode == OpCode.INPUT:
                    prompt = self.stack.pop() if operand else ""
                    if not isinstance(prompt, str):
                        raise RuntimeError("INPUT prompt must be a string.")
                    try:
                        self.stack.append(input(prompt))
                    except EOFError as error:
                        raise RuntimeError("Console input reached EOF.") from error

                elif opcode == OpCode.CALL:
                    if not isinstance(operand, tuple):
                        raise RuntimeError(
                            "CALL requires function metadata."
                        )

                    name, argument_count = operand

                    instance = None
                    if "." in name:
                        object_name, method_name = name.split(".", 1)
                        if object_name in variables and isinstance(variables[object_name], dict):
                            instance = variables[object_name]
                            function = self.class_methods.get((instance["__type__"], method_name))
                            if function is None:
                                raise RuntimeError(f"Unknown method '{method_name}'.")
                        else:
                            function = self.functions.get(name)
                    else:
                        function = self.functions.get(name)
                    if function is None:
                        raise RuntimeError(f"Unknown function '{name}'.")
                    parameters = function["parameters"]

                    if len(parameters) != argument_count:
                        raise RuntimeError(
                            f"Function '{name}' argument count mismatch."
                        )

                    if argument_count < 0 or len(self.stack) < argument_count:
                        raise RuntimeError(f"Function '{name}' argument stack underflow.")
                    arguments = [
                        self.stack.pop()
                        for _ in range(argument_count)
                    ]
                    arguments.reverse()

                    local_variables = dict(
                        zip(parameters, arguments)
                    )
                    if instance is not None:
                        local_variables["this"] = instance

                    result = self.execute(
                        function["instructions"],
                        local_variables,
                        frame_name=name,
                        isolate_stack=True,
                    )

                    if function.get("return_type") == "void":
                        continue

                    if result is None:
                        raise RuntimeError(
                            f"Function '{name}' did not return a value."
                        )

                    self.stack.append(result)

                elif opcode == OpCode.RETURN:
                    has_value = bool(operand)
                    if not has_value:
                        return _ScopedReturn(None) if scoped else None
                    if not self.stack:
                        raise RuntimeError(
                            "RETURN requires a stack value."
                        )
                    value = self.stack.pop()
                    return _ScopedReturn(value) if scoped else value

                elif opcode == OpCode.HALT:
                    return None

                else:
                    raise RuntimeError(
                        f"Unknown opcode: {opcode}"
                    )

            except Exception as error:
                if self.last_diagnostic is None:
                    self.last_diagnostic = make_diagnostic(
                        error, self.call_frames, ip - 1, opcode
                    )
                self._emit_debug("error", ip - 1, opcode, error)
                raise
            finally:
                if profiler is not None and started_ns is not None:
                    profiler.record(opcode, function_name, started_ns)

        return None
        # Finish current execution frame
