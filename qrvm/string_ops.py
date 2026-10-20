"""Canonical bootstrap QVM string operations.

Indices and lengths count Unicode code points, not UTF-8 bytes or graphemes.
"""


class StringOperationError(RuntimeError):
    """Invalid string operation or range."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise StringOperationError(f"{label} requires a string.")
    return value


def _index(value: object, label: str) -> int:
    if type(value) is not int:
        raise StringOperationError(f"{label} requires an integer.")
    return value


def string_length(value: object) -> int:
    """Return the number of Unicode code points in a string."""
    return len(_text(value, "length"))


def string_operation(name: str, arguments: list[object]) -> object:
    """Execute an existing QVM string opcode without changing its ABI."""
    arity = {"substring": 3, "find": 2, "replace": 3, "trim": 1,
             "to_string": 1, "to_int": 1, "to_double": 1}
    if name not in arity:
        raise StringOperationError(f"Unknown string operation '{name}'.")
    if len(arguments) != arity[name]:
        raise StringOperationError(f"String operation '{name}' requires {arity[name]} arguments.")
    if name == "substring":
        text = _text(arguments[0], "substring")
        start = _index(arguments[1], "substring start")
        count = _index(arguments[2], "substring length")
        if start < 0 or count < 0 or start > len(text) or count > len(text) - start:
            raise StringOperationError("Substring range out of bounds.")
        return text[start:start + count]
    if name == "find":
        return _text(arguments[0], "find").find(_text(arguments[1], "find"))
    if name == "replace":
        return _text(arguments[0], "replace").replace(
            _text(arguments[1], "replace"), _text(arguments[2], "replace"))
    if name == "trim":
        return _text(arguments[0], "trim").strip()
    if name == "to_string":
        return ("true" if arguments[0] else "false") if isinstance(arguments[0], bool) else str(arguments[0])
    if name == "to_int":
        try:
            return int(_text(arguments[0], "to_int"), 10)
        except ValueError as error:
            raise StringOperationError("String conversion failed in 'to_int'.") from error
    if name == "to_double":
        try:
            return float(_text(arguments[0], "to_double"))
        except ValueError as error:
            raise StringOperationError("String conversion failed in 'to_double'.") from error
    raise AssertionError("unreachable")
