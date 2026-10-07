from dataclasses import fields, is_dataclass
from pathlib import Path

from .ast_nodes import FunctionCall, FunctionDefinition, ImportStatement
from .lexer import Lexer
from .parser import Parser


class ModuleLoadError(Exception):
    pass


class ModuleLoader:
    def __init__(self, project_root):
        self.project_root = Path(project_root).resolve()
        self.loading_stack = []

    def load(self, source_file):
        source_path = Path(source_file).resolve()
        return self._load_file(source_path, None)
        # Return resolved multi-file program

    def _parse_file(self, source_path):
        source = source_path.read_text(encoding="utf-8")
        tokens = Lexer(source).tokenize()
        return Parser(tokens).parse()
        # Return parsed source program

    def _resolve_module_path(self, module_path):
        relative_path = Path(*module_path.split(".")).with_suffix(".vq")
        source_path = (self.project_root / relative_path).resolve()

        try:
            source_path.relative_to(self.project_root)
        except ValueError as error:
            raise ModuleLoadError(
                f"Module path escapes project root: {module_path}"
            ) from error

        if not source_path.is_file():
            raise ModuleLoadError(
                f"Module not found: {module_path}"
            )

        return source_path
        # Return canonical module source path

    def _load_file(self, source_path, namespace):
        canonical = source_path.resolve()

        if canonical in self.loading_stack:
            cycle_start = self.loading_stack.index(canonical)
            cycle = self.loading_stack[cycle_start:] + [canonical]
            names = [self._display_module(path) for path in cycle]
            raise ModuleLoadError(
                "Circular module dependency: " + " -> ".join(names)
            )

        self.loading_stack.append(canonical)
        try:
            program = self._parse_file(canonical)
            imports = [
                statement
                for statement in program
                if isinstance(statement, ImportStatement)
            ]
            local_program = [
                statement
                for statement in program
                if not isinstance(statement, ImportStatement)
            ]

            seen_modules = set()
            imported_program = []

            for declaration in imports:
                if declaration.module_path in seen_modules:
                    raise ModuleLoadError(
                        f"Duplicate import: {declaration.module_path}"
                    )
                seen_modules.add(declaration.module_path)

                module_file = self._resolve_module_path(
                    declaration.module_path
                )
                binding = declaration.alias or declaration.module_path
                imported_program.extend(
                    self._load_file(module_file, binding)
                )

            if namespace is not None:
                local_program = self._namespace_program(
                    local_program,
                    namespace,
                )

            return imported_program + local_program
        finally:
            self.loading_stack.pop()

    def _namespace_program(self, program, namespace):
        local_functions = {
            statement.name
            for statement in program
            if isinstance(statement, FunctionDefinition)
        }

        for statement in program:
            self._rewrite_calls(
                statement,
                local_functions,
                namespace,
            )

            if isinstance(statement, FunctionDefinition):
                statement.name = f"{namespace}.{statement.name}"

        return program
        # Return namespaced module statements

    def _rewrite_calls(self, value, local_functions, namespace):
        if isinstance(value, FunctionCall):
            if value.name in local_functions:
                value.name = f"{namespace}.{value.name}"

        if is_dataclass(value):
            for field in fields(value):
                self._rewrite_calls(
                    getattr(value, field.name),
                    local_functions,
                    namespace,
                )
            return

        if isinstance(value, list):
            for item in value:
                self._rewrite_calls(
                    item,
                    local_functions,
                    namespace,
                )

    def _display_module(self, source_path):
        try:
            relative = source_path.relative_to(self.project_root)
        except ValueError:
            return source_path.stem

        return ".".join(relative.with_suffix("").parts)
        # Return readable module path
