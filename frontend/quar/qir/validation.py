"""Structural validation for canonical QIR control flow."""
from .model import QBranch, QFunction, QJump, QModule, QReturn, QMetadata
from .operations import QIROperationError, validate_instruction
from .types import canonical_type
from .dataflow import QIRDataflowError, validate_dataflow

_SAFETY_CHECKS = frozenset({"bounds", "null", "lifetime", "overflow", "division_zero", "cast"})

def _validate_metadata(metadata: QMetadata | None) -> None:
    if metadata is None:
        return
    if not isinstance(metadata, QMetadata):
        raise QIRValidationError("Invalid QIR metadata object")
    source = metadata.source
    if source is not None and (not isinstance(source.file, str) or not source.file or
                               type(source.line) is not int or source.line < 1 or
                               type(source.column) is not int or source.column < 1):
        raise QIRValidationError("Invalid source location")
    safety = metadata.safety
    if (not isinstance(safety.checks, tuple) or
            any(not isinstance(item, str) or item not in _SAFETY_CHECKS for item in safety.checks) or
            len(set(safety.checks)) != len(safety.checks) or
            not isinstance(safety.inspector_tags, tuple) or
            any(not isinstance(item, str) or not item.strip() for item in safety.inspector_tags) or
            len(set(safety.inspector_tags)) != len(safety.inspector_tags)):
        raise QIRValidationError("Invalid safety metadata")

class QIRValidationError(ValueError):
    """Raised when a QIR graph violates structural invariants."""

def validate_function(function: QFunction) -> None:
    if not function.name or not function.blocks:
        raise QIRValidationError("Function needs a name and at least one block")
    try:
        canonical_type(function.return_type.name)
        for parameter in function.parameters:
            canonical_type(parameter.type.name)
            if parameter.type.name == "void":
                raise QIRValidationError("Parameter cannot have void type")
    except ValueError as exc:
        raise QIRValidationError(str(exc)) from exc
    labels = [block.label for block in function.blocks]
    if any(not label for label in labels) or len(set(labels)) != len(labels):
        raise QIRValidationError("Block labels must be unique and nonempty")
    known = set(labels)
    for block in function.blocks:
        for instruction in block.instructions:
            _validate_metadata(instruction.metadata)
            try:
                validate_instruction(instruction)
            except QIROperationError as exc:
                raise QIRValidationError(f"Block {block.label}: {exc}") from exc
        terminator = block.terminator
        if isinstance(terminator, QJump):
            targets = (terminator.target,)
        elif isinstance(terminator, QBranch):
            if terminator.condition.type.name != "bool":
                raise QIRValidationError("Branch condition must be bool")
            targets = (terminator.true_target, terminator.false_target)
        elif isinstance(terminator, QReturn):
            if terminator.value is None and function.return_type.name != "void":
                raise QIRValidationError("Non-void function must return a value")
            if terminator.value is not None and terminator.value.type != function.return_type:
                raise QIRValidationError("Return type mismatch")
            targets = ()
        else:
            raise QIRValidationError("Unknown block terminator")
        if any(target not in known for target in targets):
            raise QIRValidationError("Branch target does not exist")

    # Validate phi structure before dataflow (which assumes valid edges).
    predecessors: dict[str, set[str]] = {label: set() for label in labels}
    for block in function.blocks:
        term = block.terminator
        targets = ((term.target,) if isinstance(term, QJump) else
                   (term.true_target, term.false_target) if isinstance(term, QBranch) else ())
        for target in targets:
            predecessors[target].add(block.label)
    entry = function.blocks[0].label
    for block in function.blocks:
        if block.phis and block.label == entry:
            raise QIRValidationError("Entry block cannot contain phi nodes")
        for phi in block.phis:
            _validate_metadata(phi.metadata)
            try:
                canonical_type(phi.result.type.name)
            except ValueError as exc:
                raise QIRValidationError(str(exc)) from exc
            sources = [source for source, _ in phi.incoming]
            if (not sources or len(sources) != len(set(sources)) or
                    set(sources) != predecessors[block.label]):
                raise QIRValidationError(f"Block {block.label}: phi incoming edges must match predecessors")
            for _, value in phi.incoming:
                if value.type != phi.result.type:
                    raise QIRValidationError(f"Block {block.label}: phi type mismatch")

    try:
        validate_dataflow(function)
    except QIRDataflowError as exc:
        raise QIRValidationError(str(exc)) from exc

def validate_module(module: QModule) -> None:
    if not module.name:
        raise QIRValidationError("Module name cannot be empty")
    names = [function.name for function in module.functions]
    if len(names) != len(set(names)):
        raise QIRValidationError("Duplicate function name")
    for function in module.functions:
        validate_function(function)
