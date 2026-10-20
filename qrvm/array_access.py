"""Canonical bootstrap array indexing and shape checks for QRVM."""


class ArrayAccessError(RuntimeError):
    """Invalid array shape or index in QRVM."""


def validate_shape(size: int, second_size: int | None) -> None:
    """Reject malformed dimensions before allocating an array."""
    if type(size) is not int or size < 0:
        raise ArrayAccessError("Array size must be a non-negative int.")
    if second_size is not None:
        if type(second_size) is not int or second_size <= 0:
            raise ArrayAccessError("Second array dimension must be a positive int.")
        if size % second_size:
            raise ArrayAccessError("Array size must be divisible by its second dimension.")


def resolve_index(array_object: dict, first: object, second: object = None, *, two_dimensional: bool = False) -> int:
    """Return a checked flat index for a one- or two-dimensional array."""
    values = array_object["__array__"]
    if two_dimensional:
        width = array_object.get("__second_size__")
        if width is None:
            raise ArrayAccessError("Second index requires multidimensional array.")
        validate_shape(len(values), width)
        rows = len(values) // width
        if (type(first) is not int or type(second) is not int or
                first < 0 or first >= rows or second < 0 or second >= width):
            raise ArrayAccessError(f"Array index out of bounds: [{first}][{second}].")
        return first * width + second
    if type(first) is not int:
        raise ArrayAccessError("Array index must be int.")
    if first < 0 or first >= len(values):
        raise ArrayAccessError(f"Array index out of bounds: {first}.")
    return first
