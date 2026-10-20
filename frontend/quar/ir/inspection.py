"""Deterministic text inspection of Quar IR module and symbol identities."""


def format_project(project) -> str:
    """Return a human-readable inventory without relying on AST or backends."""
    lines = []
    for module in project.modules:
        lines.append(f"module {module.module_id}")
        for dependency in module.dependencies:
            lines.append(f"  depends {dependency}")
        for function in module.functions:
            parameters = ", ".join(f"{name}: {kind}" for name, kind in function.parameters)
            lines.append(f"  function {function.symbol}({parameters}) -> {function.return_type}")
            if function.body:
                lines.append(f"    statements {len(function.body)}")
    return "\n".join(lines) + ("\n" if lines else "")
