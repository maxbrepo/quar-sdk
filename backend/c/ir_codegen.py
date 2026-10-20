"""Experimental single-translation-unit C emitter for resolved Quar IR.

Only the explicitly supported IR subset is emitted. Top-level Quar statements
are not represented in IR 0.1 and therefore are not generated here.
"""
from frontend.quar.ir import (IRLiteral, IRReference, IRBinary, IRCall,
                              IRDeclare, IRAssign, IRReturn, validate_project)


class IRCodegenError(ValueError):
    """Unsupported or invalid IR-to-C conversion."""


class IRCodeGenerator:
    def __init__(self):
        self._names = {}

    @staticmethod
    def _identifier(name):
        return "vq_" + name.encode("utf-8").hex()

    @staticmethod
    def _type(name):
        types = {"int": "int", "double": "double"}
        if name not in types:
            raise IRCodegenError(f"Unsupported C type: {name}")
        return types[name]

    def _expression(self, node):
        if isinstance(node, IRLiteral):
            if type(node.value) not in (int, float):
                raise IRCodegenError("Unsupported literal")
            return repr(node.value)
        if isinstance(node, IRReference):
            return node.name
        if isinstance(node, IRBinary):
            if node.operator not in {"+", "-", "*", "/"}:
                raise IRCodegenError(f"Unsupported binary operator: {node.operator}")
            return f"({self._expression(node.left)} {node.operator} {self._expression(node.right)})"
        if isinstance(node, IRCall):
            if node.symbol not in self._names:
                raise IRCodegenError(f"Unknown function: {node.symbol}")
            args = ", ".join(self._expression(arg) for arg in node.arguments)
            return f"{self._names[node.symbol]}({args})"
        raise IRCodegenError(f"Unsupported expression: {type(node).__name__}")

    def _statement(self, node):
        if isinstance(node, IRReturn):
            return f"return {self._expression(node.value)};"
        if isinstance(node, IRDeclare):
            return f"{self._type(node.type_name)} {node.name} = {self._expression(node.value)};"
        if isinstance(node, IRAssign):
            return f"{node.name} = {self._expression(node.value)};"
        if isinstance(node, IRCall):
            return self._expression(node) + ";"
        raise IRCodegenError(f"Unsupported statement: {type(node).__name__}")

    def _signature(self, function):
        params = ", ".join(f"{self._type(kind)} {name}" for name, kind in function.parameters) or "void"
        return f"{self._type(function.return_type)} {self._names[function.symbol]}({params})"

    def generate(self, project):
        """Generate one C translation unit containing all IR functions."""
        validate_project(project)
        functions = [fn for module in project.modules for fn in module.functions]
        self._names = {fn.symbol: self._identifier(fn.symbol) for fn in functions}
        lines = ["/* Generated from Quar IR 0.1; functions only. */", ""]
        lines.extend(self._signature(fn) + ";" for fn in functions)
        lines.append("")
        for fn in functions:
            lines.append(self._signature(fn) + " {")
            lines.extend("    " + self._statement(stmt) for stmt in fn.body)
            lines.extend(["}", ""])
        if project.entry_module is not None:
            lines.extend(self._main_lines(project))
        return "\n".join(lines)

    def _main_lines(self, project):
        lines = ["int main(void) {"]
        lines.extend("    " + self._statement(stmt) for stmt in project.entry_body)
        if not any(isinstance(stmt, IRReturn) for stmt in project.entry_body):
            lines.append("    return 0;")
        return lines + ["}", ""]

    def generate_split(self, project):
        """Return independent C translation units and one shared declarations header.

        The caller owns file naming, writing, compilation and linking. Module
        identities are encoded in filenames to avoid collisions and traversal.
        """
        validate_project(project)
        functions = [fn for module in project.modules for fn in module.functions]
        self._names = {fn.symbol: self._identifier(fn.symbol) for fn in functions}
        header_name = "quar_generated.h"
        header = ["/* Quar IR 0.1: shared C declarations. */", "#ifndef QUAR_GENERATED_H",
                  "#define QUAR_GENERATED_H", ""]
        header.extend(self._signature(fn) + ";" for fn in functions)
        header.extend(["", "#endif /* QUAR_GENERATED_H */", ""])
        outputs = {header_name: "\n".join(header)}
        for module in project.modules:
            filename = self._identifier(module.module_id) + ".c"
            lines = [f"/* Quar module: {module.module_id} */",
                     f'#include "{header_name}"', ""]
            for fn in module.functions:
                lines.append(self._signature(fn) + " {")
                lines.extend("    " + self._statement(stmt) for stmt in fn.body)
                lines.extend(["}", ""])
            if module.module_id == project.entry_module:
                lines.extend(self._main_lines(project))
            outputs[filename] = "\n".join(lines)
        return outputs
