"""Canonical bootstrap struct field operations over existing QRVM dictionaries.

These checks preserve the legacy object layout and reference identity. They do
not enforce compile-time field types or ownership/lifetime guarantees.
"""


class StructAccessError(RuntimeError):
    """Invalid struct declaration or member access."""


def validate_fields(type_name: str, field_names: object) -> tuple[str, ...]:
    """Validate a declaration and return an ordered field-name tuple."""
    if not isinstance(type_name, str) or not type_name:
        raise StructAccessError("Struct type name must be a nonempty string.")
    if not isinstance(field_names, (tuple, list)):
        raise StructAccessError("Struct fields must be a sequence.")
    names = tuple(field_names)
    if any(not isinstance(name, str) or not name for name in names):
        raise StructAccessError("Struct field names must be nonempty strings.")
    if len(set(names)) != len(names):
        raise StructAccessError("Duplicate struct field name.")
    return names


def create_struct(type_name: str, field_names: object, values: object) -> dict:
    """Build a legacy-compatible struct with its declared field order."""
    names = validate_fields(type_name, field_names)
    items = tuple(values)
    if len(names) != len(items):
        raise StructAccessError("Struct field/value count mismatch.")
    return {"__type__": type_name, "__fields__": dict(zip(names, items))}


def resolve_field(variables: dict, object_name: str, member_name: str) -> dict:
    """Return a validated field dictionary without changing its identity."""
    if object_name not in variables:
        raise StructAccessError(f"Unknown object '{object_name}'.")
    obj = variables[object_name]
    if not isinstance(obj, dict) or not isinstance(obj.get("__fields__"), dict):
        raise StructAccessError(f"'{object_name}' is not an object.")
    fields = obj["__fields__"]
    if member_name not in fields:
        raise StructAccessError(f"Unknown field '{member_name}'.")
    return fields


def load_field(variables: dict, object_name: str, member_name: str) -> object:
    """Read a field, preserving shared references."""
    return resolve_field(variables, object_name, member_name)[member_name]


def store_field(variables: dict, object_name: str, member_name: str, value: object) -> None:
    """Update an existing field without changing the containing object."""
    resolve_field(variables, object_name, member_name)[member_name] = value
