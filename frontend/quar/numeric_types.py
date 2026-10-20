INTEGER_BITS = {
    "i8": (8, True),
    "i16": (16, True),
    "i32": (32, True),
    "i64": (64, True),
    "i128": (128, True),
    "u8": (8, False),
    "u16": (16, False),
    "u32": (32, False),
    "u64": (64, False),
    "u128": (128, False),
}

FLOAT_BITS = {
    "f32": 32,
    "f64": 64,
    "long_double": 80,
}

TYPE_ALIASES = {
    "byte": "u8",
    "int": "i32",
    "float": "f32",
    "double": "f64",
    "short": "i16",
    "ushort": "u16",
    "uint": "u32",
    "long": "i64",
    "ulong": "u64",
    "llong": "i128",
    "ullong": "u128",
}

def canonical_numeric_type(type_name):
    return TYPE_ALIASES.get(type_name, type_name)

def integer_range(type_name):
    type_name = canonical_numeric_type(type_name)
    bits, signed = INTEGER_BITS[type_name]
    if signed:
        return -(2 ** (bits - 1)), (2 ** (bits - 1)) - 1
    return 0, (2 ** bits) - 1

def is_integer_type(type_name):
    return canonical_numeric_type(type_name) in INTEGER_BITS

def is_float_type(type_name):
    return canonical_numeric_type(type_name) in FLOAT_BITS

def is_numeric_type(type_name):
    return is_integer_type(type_name) or is_float_type(type_name)

def integer_conversion_is_safe(source, target):
    source = canonical_numeric_type(source)
    target = canonical_numeric_type(target)
    if source not in INTEGER_BITS or target not in INTEGER_BITS:
        return False
    source_min, source_max = integer_range(source)
    target_min, target_max = integer_range(target)
    return target_min <= source_min and source_max <= target_max
