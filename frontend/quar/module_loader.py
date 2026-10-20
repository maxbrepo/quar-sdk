from dataclasses import dataclass, fields, is_dataclass
from copy import deepcopy
from pathlib import Path

from .ast_nodes import FunctionCall, FunctionDefinition, ImportStatement, VariantConstructor
from .lexer import Lexer
from .parser import Parser


@dataclass(frozen=True)
class ModuleRecord:
    """One physical source module, independent of import aliases."""
    path: Path
    statements: tuple
    dependencies: tuple
    bindings: tuple
    symbols: tuple


class ModuleLoadError(Exception):
    pass


class ModuleLoader:
    def __init__(self, project_root, *, kart_project=None):
        self.project_root = Path(project_root).resolve()
        self.kart_project = Path(kart_project).resolve() if kart_project is not None else None
        self.loading_stack = []
        self.parse_cache = {}
        self.dependencies = {}
        self.parse_counts = {}
        self.import_bindings = {}
        self.module_records = {}

    def load(self, source_file):
        source_path = Path(source_file).resolve()
        self.loading_stack.clear()
        self.dependencies.clear()
        self.parse_cache.clear()
        self.parse_counts.clear()
        self.import_bindings.clear()
        self.module_records.clear()
        return self._load_file(source_path, None)
        # Return resolved multi-file program

    def module_bindings(self, source_file):
        """Return local import bindings mapped to canonical module paths."""
        return dict(self.import_bindings.get(Path(source_file).resolve(), {}))

    def symbol_id(self, source_file, symbol_name):
        """Return a stable, module-scoped symbol identity.

        Identity is independent of the local alias used by an importer.
        """
        canonical = Path(source_file).resolve()
        record = self.module_records.get(canonical)
        if record is None or symbol_name not in record.symbols:
            raise ModuleLoadError(f"Unknown module symbol: {symbol_name}")
        return (canonical, symbol_name)

    def canonical_program(self):
        """Lower module definitions and calls to canonical module identities.

        This experimental view does not replace the legacy load() output.
        """
        result = []
        records = self.project_modules()
        entry = self.dependency_order()[-1] if records else None
        for record in records:
            prefix = self._display_module(record.path)
            local_symbols = set(record.symbols)
            bindings = dict(record.bindings)
            statements = list(deepcopy(record.statements))
            for index, statement in enumerate(statements):
                statement = self._canonicalize_calls(statement, prefix, local_symbols, bindings,
                                                     is_entry=(record.path == entry))
                if isinstance(statement, FunctionDefinition) and record.path != entry:
                    statement.name = f"{prefix}.{statement.name}"
                statements[index] = statement
            result.extend(statements)
        return result

    def _canonicalize_calls(self, value, prefix, local_symbols, bindings, is_entry=False):
        """Resolve imported functions while preserving genuine enum constructors."""
        if isinstance(value, VariantConstructor):
            module_path = bindings.get(value.enum_name)
            if module_path is not None:
                symbol = value.variant_name
                self.symbol_id(module_path, symbol)
                value = FunctionCall(
                    f"{self._display_module(module_path)}.{symbol}", value.arguments
                )
        if isinstance(value, FunctionCall):
            name = value.name
            if name in local_symbols:
                value.name = name if is_entry else f"{prefix}.{name}"
            else:
                for alias, module_path in sorted(bindings.items(), key=lambda item: -len(item[0])):
                    if name.startswith(alias + "."):
                        symbol = name[len(alias) + 1:]
                        self.symbol_id(module_path, symbol)
                        value.name = f"{self._display_module(module_path)}.{symbol}"
                        break
        if is_dataclass(value):
            for field in fields(value):
                setattr(value, field.name, self._canonicalize_calls(
                    getattr(value, field.name), prefix, local_symbols, bindings, is_entry
                ))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                value[index] = self._canonicalize_calls(
                    item, prefix, local_symbols, bindings, is_entry
                )
        elif isinstance(value, tuple):
            value = tuple(self._canonicalize_calls(
                item, prefix, local_symbols, bindings, is_entry
            ) for item in value)
        return value

    def project_modules(self):
        """Return physical module records in dependency-first order."""
        return tuple(self.module_records[path] for path in self.dependency_order())

    def dependency_order(self):
        """Return canonical module paths, dependencies before importers.

        Each module appears exactly once. Call after a successful load().
        This ordering is suitable for a future per-module IR/build pipeline.
        """
        visited = set()
        ordered = []

        def visit(module):
            if module in visited:
                return
            visited.add(module)
            for dependency in self.dependencies.get(module, []):
                visit(dependency)
            ordered.append(module)

        for module in self.dependencies:
            visit(module)
        return ordered

    def _parse_file(self, source_path):
        canonical = source_path.resolve()
        if canonical not in self.parse_cache:
            source = canonical.read_text(encoding="utf-8")
            tokens = Lexer(source).tokenize()
            self.parse_cache[canonical] = Parser(tokens).parse()
            self.parse_counts[canonical] = self.parse_counts.get(canonical, 0) + 1
        return deepcopy(self.parse_cache[canonical])
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

        if self.kart_project is not None:
            from kart.core import KartError, installed_packages
            from kart.module_paths import resolve_package_module
            try:
                packages = installed_packages(self.kart_project)
                package, separator, module = module_path.partition(".")
                if package in packages:
                    if source_path.is_file():
                        raise ModuleLoadError(
                            f"Ambiguous local and Kart import: {module_path}"
                        )
                    if not separator:
                        raise ModuleLoadError(
                            f"Kart import requires a module: {module_path}"
                        )
                    return resolve_package_module(self.kart_project, package, module)
            except KartError as error:
                raise ModuleLoadError(f"Kart dependency error: {error}") from error

        if not source_path.is_file():
            raise ModuleLoadError(f"Module not found: {module_path}")

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
            seen_bindings = set()
            imported_program = []
            self.dependencies[canonical] = []
            self.import_bindings[canonical] = {}

            for declaration in imports:
                if declaration.module_path in seen_modules:
                    raise ModuleLoadError(
                        f"Duplicate import: {declaration.module_path}"
                    )
                seen_modules.add(declaration.module_path)

                module_file = self._resolve_module_path(
                    declaration.module_path
                )
                self.dependencies[canonical].append(module_file)
                binding = declaration.alias or declaration.module_path
                if binding in seen_bindings:
                    raise ModuleLoadError(f"Duplicate import binding: {binding}")
                seen_bindings.add(binding)
                self.import_bindings[canonical][binding] = module_file
                imported_program.extend(
                    self._load_file(module_file, binding)
                )

            if canonical not in self.module_records:
                self.module_records[canonical] = ModuleRecord(
                    canonical, tuple(deepcopy(local_program)),
                    tuple(self.dependencies[canonical]),
                    tuple(self.import_bindings[canonical].items()),
                    tuple(statement.name for statement in local_program
                          if isinstance(statement, FunctionDefinition)),
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
