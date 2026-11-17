"""Canonical, fail-closed function signature table for future QIR calls.

This does not enable inter-function call lowering or C emission.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from .model import QFunction, QType
from .types import canonical_type


class QIRSignatureError(ValueError):
    """Invalid or ambiguous function declaration or call."""


@dataclass(frozen=True)
class QFunctionSignature:
    name: str
    parameters: tuple[QType, ...]
    return_type: QType


class QFunctionSignatures:
    """Immutable index of validated QIR function declarations."""

    def __init__(self, functions: Iterable[QFunction]):
        signatures: dict[str, QFunctionSignature] = {}
        for function in functions:
            if not isinstance(function, QFunction) or not function.name or not function.name.isidentifier():
                raise QIRSignatureError("Invalid QIR function declaration")
            if function.name in signatures:
                raise QIRSignatureError(f"Duplicate QIR function: {function.name}")
            try:
                result = canonical_type(function.return_type.name)
                parameters = tuple(canonical_type(param.type.name) for param in function.parameters)
            except (ValueError, AttributeError) as exc:
                raise QIRSignatureError(f"Invalid type in function: {function.name}") from exc
            if any(param.name == "void" for param in parameters):
                raise QIRSignatureError("Function parameters cannot be void")
            signatures[function.name] = QFunctionSignature(function.name, parameters, result)
        self._signatures = signatures

    def resolve(self, name: str, argument_types: tuple[QType, ...], expected: QType) -> QFunctionSignature:
        """Check exact argument and result types, with no implicit conversions."""
        signature = self._signatures.get(name)
        if signature is None:
            raise QIRSignatureError(f"Unknown QIR function: {name}")
        if signature.parameters != argument_types:
            raise QIRSignatureError(f"QIR call argument mismatch: {name}")
        if signature.return_type != expected:
            raise QIRSignatureError(f"QIR call result mismatch: {name}")
        return signature
