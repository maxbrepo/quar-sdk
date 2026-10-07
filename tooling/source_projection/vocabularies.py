from .profiles import VocabularyStyle
from .languages import LANGUAGES, get_language_data

# Canonical words are defined once; localized display forms live in languages/*.py.
CANONICAL_KEYS = (
    "i8", "i16", "i32", "i64", "i128", "u8", "u16", "u32", "u64", "u128", "f32", "f64",
    "bool", "char", "string", "void", "tuple", "const", "alias", "struct", "record", "enum",
    "if", "else", "while", "do", "for", "loop", "switch", "case", "default", "match",
    "break", "continue", "return", "import", "as", "and", "or", "not", "true", "false",
)
CANONICAL_WORDS = {key: key for key in CANONICAL_KEYS}


CANONICAL_BUILTINS = ("print", "sum")

def display_builtin(canonical, profile):
    """Return the localized display spelling for a canonical built-in."""
    if profile.vocabulary == VocabularyStyle.CANONICAL:
        return canonical
    data = get_language_data(profile.language)
    return data.EASY_WORDS.get(canonical, canonical)

LEGACY_ALIASES = {
    "int": "i32", "byte": "u8", "float": "f32", "double": "f64", "short": "i16",
    "ushort": "u16", "uint": "u32", "long": "i64", "ulong": "u64", "llong": "i128", "ullong": "u128",
}

def display_word(canonical, profile):
    if profile.vocabulary == VocabularyStyle.CANONICAL:
        return canonical
    data = get_language_data(profile.language)
    if canonical in data.EXTENDED_TYPES:
        return data.EXTENDED_TYPES[canonical]
    return data.WORDS.get(canonical, canonical)

def input_map(profile):
    data = get_language_data(profile.language)
    result = dict(LEGACY_ALIASES)
    for canonical in CANONICAL_KEYS:
        result[canonical] = canonical
        localized = data.WORDS.get(canonical)
        if localized:
            result[localized] = canonical
        extended = data.EXTENDED_TYPES.get(canonical)
        if extended:
            result[extended] = canonical
    for canonical in CANONICAL_BUILTINS:
        result[canonical] = canonical
        localized = data.EASY_WORDS.get(canonical)
        if localized:
            result[localized] = canonical
    return result
