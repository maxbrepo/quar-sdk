from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureStatus:
    name: str
    maturity: str
    dependency: str = "NONE"
    qrvm: str = "SUPPORTED"
    native: str = "SUPPORTED"
    validation: str = "PASS"
    since: str = "0.0.3"
    notes: str = ""


FEATURES = [
    FeatureStatus("Fixed-width numeric types", "STABLE"),
    FeatureStatus("Constants", "STABLE"),
    FeatureStatus("Conditions and truthiness", "STABLE"),
    FeatureStatus("Case selection", "STABLE"),
    FeatureStatus("Counter loops", "STABLE"),
    FeatureStatus("Loop diagnostics", "EXPERIMENTAL", "OTHER"),
    FeatureStatus("Functions", "STABLE"),
    FeatureStatus("Default arguments", "STABLE"),
    FeatureStatus("Named arguments", "STABLE"),
    FeatureStatus("Static arrays", "STABLE"),
    FeatureStatus("Multidimensional arrays", "STABLE"),
    FeatureStatus(
        "Dynamic arrays",
        "EXPERIMENTAL",
        "MEMORY_MODEL",
        "SUPPORTED",
        "PENDING",
        "PARTIAL",
        "0.0.3",
        "Ownership, lifetime, native allocation and resizing API are pending.",
    ),
    FeatureStatus("Slices", "PLANNED", "MEMORY_MODEL", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("Collections", "PLANNED", "GENERICS", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("Iterators", "PLANNED", "GENERICS", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("State machines", "PLANNED", "OOP", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("Unicode strings", "STABLE"),
    FeatureStatus("String concatenation and comparison", "STABLE"),
    FeatureStatus("String length and indexing", "STABLE"),
    FeatureStatus("String substring copy", "STABLE"),
    FeatureStatus("String find, replace and trim", "STABLE"),
    FeatureStatus("Number and string conversion", "STABLE"),
    FeatureStatus(
        "Unicode code-point iteration",
        "EXPERIMENTAL",
        "OTHER",
        "SUPPORTED",
        "PENDING",
        "PASS",
        "0.0.3",
        "QRVM iterates Unicode code points; grapheme-cluster policy is not final.",
    ),
    FeatureStatus("String split", "PLANNED", "GENERICS", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("String interpolation", "PLANNED", "OTHER", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("Advanced string formatting", "PLANNED", "OTHER", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("Multiline strings", "PLANNED", "OTHER", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("Raw strings", "PLANNED", "OTHER", "PENDING", "PENDING", "NOT_TESTED"),
    FeatureStatus("Struct", "STABLE"),
    FeatureStatus("Record", "STABLE"),
    FeatureStatus("Enum", "STABLE"),
    FeatureStatus("Type aliases", "STABLE"),
    FeatureStatus("Tuples", "EXPERIMENTAL", "TYPE_SYSTEM", "SUPPORTED", "PENDING", "PASS"),
    FeatureStatus("Tuple destructuring", "EXPERIMENTAL", "TYPE_SYSTEM", "SUPPORTED", "PENDING", "PASS"),
    FeatureStatus("Enum associated values", "EXPERIMENTAL", "TYPE_SYSTEM", "SUPPORTED", "PENDING", "PASS"),
    FeatureStatus("Tagged unions", "EXPERIMENTAL", "TYPE_SYSTEM", "SUPPORTED", "PENDING", "PASS", "0.0.3", "Canonical form: enum variants with associated values."),
    FeatureStatus("Match", "EXPERIMENTAL", "TYPE_SYSTEM", "SUPPORTED", "PENDING", "PASS", "0.0.3", "Supports variant matching, payload binding and exhaustiveness checks."),
    FeatureStatus("Native module backend", "EXPERIMENTAL", "NATIVE_BACKEND", "SUPPORTED", "PENDING", "PARTIAL"),
]


VIEWS = [
    ("Stable", lambda f: f.maturity == "STABLE"),
    ("Experimental", lambda f: f.maturity == "EXPERIMENTAL"),
    ("Planned", lambda f: f.maturity == "PLANNED"),
    ("Deprecated", lambda f: f.maturity == "DEPRECATED"),
    ("Disabled", lambda f: f.maturity == "DISABLED"),
    ("Memory Model", lambda f: f.dependency == "MEMORY_MODEL"),
    ("Type System", lambda f: f.dependency == "TYPE_SYSTEM"),
    ("Native Backend", lambda f: f.dependency == "NATIVE_BACKEND"),
    ("Other Dependencies", lambda f: f.dependency not in {"NONE", "MEMORY_MODEL", "TYPE_SYSTEM", "NATIVE_BACKEND"}),
    ("Tests / Validation", lambda f: f.validation in {"PASS", "PARTIAL", "FAIL", "NOT_TESTED"}),
    ("Overview", lambda f: True),
]
