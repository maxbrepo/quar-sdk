"""Focused loader regression tests; run with python -m unittest tests/tools/test_module_loader_13a.py."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from frontend.quar.ast_nodes import ImportStatement, FunctionDefinition, FunctionCall
from frontend.quar.module_loader import ModuleLoader, ModuleLoadError


class ModuleLoader13ATests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ("main", "left", "right", "shared"):
            (self.root / f"{name}.vq").write_text("", encoding="utf-8")

    def test_shared_dependency_parsed_once(self):
        programs = {
            "main": [ImportStatement("left", None), ImportStatement("right", None)],
            "left": [ImportStatement("shared", None)],
            "right": [ImportStatement("shared", None)],
            "shared": [],
        }
        loader = ModuleLoader(self.root)
        with patch.object(loader, "_parse_file", wraps=loader._parse_file):
            with patch("frontend.quar.module_loader.Parser") as parser:
                # Empty source fixtures: supply import ASTs for each source in traversal order.
                parser.return_value.parse.side_effect = [
                    programs["main"], programs["left"], programs["shared"], programs["right"]
                ]
                loader.load(self.root / "main.vq")
                self.assertEqual(loader.parse_counts[self.root / "shared.vq"], 1)
                self.assertEqual(len(loader.dependencies[self.root / "main.vq"]), 2)

    def test_bindings_are_local_and_share_module_identity(self):
        loader = ModuleLoader(self.root)
        programs = {
            "main": [ImportStatement("left", "a"), ImportStatement("right", "b")],
            "left": [ImportStatement("shared", "common_left")],
            "right": [ImportStatement("shared", "common_right")],
            "shared": [],
        }
        with patch.object(loader, "_parse_file", side_effect=lambda p: programs[p.stem]):
            loader.load(self.root / "main.vq")
        self.assertEqual(loader.module_bindings(self.root / "left.vq")["common_left"],
                         loader.module_bindings(self.root / "right.vq")["common_right"])
        self.assertEqual(len(loader.dependency_order()), 4)
        self.assertEqual(loader.dependency_order()[-1], self.root / "main.vq")

    def test_project_modules_are_unique_and_ordered(self):
        loader = ModuleLoader(self.root)
        programs = {
            "main": [ImportStatement("left", "l"), ImportStatement("right", "r")],
            "left": [ImportStatement("shared", "s")],
            "right": [ImportStatement("shared", "other")],
            "shared": [],
        }
        with patch.object(loader, "_parse_file", side_effect=lambda p: programs[p.stem]):
            loader.load(self.root / "main.vq")
        records = loader.project_modules()
        names = [record.path.stem for record in records]
        self.assertEqual(len(names), 4)
        self.assertEqual(names.count("shared"), 1)
        self.assertLess(names.index("shared"), names.index("left"))
        self.assertLess(names.index("shared"), names.index("right"))
        self.assertEqual(names[-1], "main")
        self.assertEqual(dict(loader.module_records[self.root / "left.vq"].bindings)["s"],
                         self.root / "shared.vq")

    def test_symbol_identity_ignores_import_alias(self):
        loader = ModuleLoader(self.root)
        programs = {
            "main": [ImportStatement("left", "l"), ImportStatement("right", "r")],
            "left": [ImportStatement("shared", "one")],
            "right": [ImportStatement("shared", "two")],
            "shared": [FunctionDefinition("int", "answer", [], [])],
        }
        with patch.object(loader, "_parse_file", side_effect=lambda p: programs[p.stem]):
            loader.load(self.root / "main.vq")
        shared = self.root / "shared.vq"
        self.assertEqual(loader.symbol_id(shared, "answer"), (shared, "answer"))
        self.assertEqual(loader.project_modules()[0].symbols, ("answer",))
        with self.assertRaisesRegex(ModuleLoadError, "Unknown module symbol"):
            loader.symbol_id(shared, "missing")

    def test_canonical_program_emits_shared_definition_once(self):
        loader = ModuleLoader(self.root)
        programs = {
            "main": [ImportStatement("left", "l"), ImportStatement("right", "r")],
            "left": [ImportStatement("shared", "s")],
            "right": [ImportStatement("shared", "t")],
            "shared": [FunctionDefinition("int", "answer", [], [])],
        }
        with patch.object(loader, "_parse_file", side_effect=lambda p: programs[p.stem]):
            loader.load(self.root / "main.vq")
        functions = [node.name for node in loader.canonical_program()
                     if isinstance(node, FunctionDefinition)]
        self.assertEqual(functions, ["shared.answer"])

    def test_canonical_calls_resolve_distinct_aliases(self):
        loader = ModuleLoader(self.root)
        programs = {
            "main": [ImportStatement("left", "l"), ImportStatement("right", "r"),
                     FunctionCall("l.use", []), FunctionCall("r.use", [])],
            "left": [ImportStatement("shared", "s"),
                     FunctionDefinition("int", "use", [], [FunctionCall("s.answer", [])])],
            "right": [ImportStatement("shared", "t"),
                      FunctionDefinition("int", "use", [], [FunctionCall("t.answer", [])])],
            "shared": [FunctionDefinition("int", "answer", [], [])],
        }
        with patch.object(loader, "_parse_file", side_effect=lambda p: programs[p.stem]):
            loader.load(self.root / "main.vq")
        lowered = loader.canonical_program()
        calls = []
        def collect(node):
            if isinstance(node, FunctionCall):
                calls.append(node.name)
            if isinstance(node, FunctionDefinition):
                for child in node.body:
                    collect(child)
        for statement in lowered:
            collect(statement)
        self.assertEqual(calls.count("shared.answer"), 2)
        self.assertIn("left.use", calls)
        self.assertIn("right.use", calls)
        self.assertEqual(sum(isinstance(node, FunctionDefinition) and
                             node.name == "shared.answer" for node in lowered), 1)

    @unittest.expectedFailure
    def test_shared_function_is_emitted_once(self):
        """Known 13A.8 gap: diamond imports duplicate physical definitions."""
        loader = ModuleLoader(self.root)
        programs = {
            "main": [ImportStatement("left", "l"), ImportStatement("right", "r")],
            "left": [ImportStatement("shared", "s")],
            "right": [ImportStatement("shared", "t")],
            "shared": [FunctionDefinition("int", "answer", [], [])],
        }
        with patch.object(loader, "_parse_file", side_effect=lambda p: programs[p.stem]):
            combined = loader.load(self.root / "main.vq")
        physical_symbols = loader.module_records[self.root / "shared.vq"].symbols
        self.assertEqual(physical_symbols, ("answer",))
        # A future canonical lowering must emit one definition for this module.
        emitted = [node for node in combined
                   if isinstance(node, FunctionDefinition) and node.name.endswith(".answer")]
        self.assertEqual(len(emitted), 1)

    def test_cycle_rejected(self):
        loader = ModuleLoader(self.root)
        with patch.object(loader, "_parse_file", side_effect=lambda p: {
            "main": [ImportStatement("left", None)],
            "left": [ImportStatement("main", None)],
        }[p.stem]):
            with self.assertRaisesRegex(ModuleLoadError, "Circular module dependency"):
                loader.load(self.root / "main.vq")

    def test_duplicate_binding_rejected(self):
        loader = ModuleLoader(self.root)
        with patch.object(loader, "_parse_file", side_effect=lambda p: {
            "main": [ImportStatement("left", "same"), ImportStatement("right", "same")],
            "left": [], "right": [],
        }[p.stem]):
            with self.assertRaisesRegex(ModuleLoadError, "Duplicate import binding"):
                loader.load(self.root / "main.vq")


if __name__ == "__main__":
    unittest.main()
